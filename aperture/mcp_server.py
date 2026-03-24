"""MCP server — Aperture's sole interface.

Exposes source crawling, knowledge base storage, harness prompts, and search
to orchestrators like OpenClaw/NemoClaw and agents like Claude Code.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from aperture.config import settings
from aperture.models import EntryMeta, RawEntry

mcp = FastMCP(
    "aperture",
    instructions=(
        "Aperture is a knowledge harness. Use fetch_sources to crawl new content, "
        "get_harness_prompt to get processing instructions, store_entry to save "
        "processed results, and search/query tools to retrieve knowledge."
    ),
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _entries_dir() -> Path:
    return settings.data_dir / "entries"


def _load_entries(days: int = 7) -> list[tuple[str, RawEntry, EntryMeta]]:
    """Load entries from the last N days."""
    entries_dir = _entries_dir()
    if not entries_dir.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    results = []

    for day_dir in sorted(entries_dir.iterdir(), reverse=True):
        if not day_dir.is_dir():
            continue
        try:
            day_date = datetime.strptime(day_dir.name, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if day_date < cutoff:
            break

        for entry_path in sorted(day_dir.glob("[0-9]*.json")):
            if entry_path.stem.endswith(".meta"):
                continue
            meta_path = day_dir / f"{entry_path.stem}.meta.json"
            if not meta_path.exists():
                continue

            entry = RawEntry.model_validate_json(entry_path.read_text(encoding="utf-8"))
            meta = EntryMeta.model_validate_json(meta_path.read_text(encoding="utf-8"))
            entry_id = f"{day_dir.name}/{entry_path.stem}"
            results.append((entry_id, entry, meta))

    return results


def _entry_to_dict(entry_id: str, entry: RawEntry, meta: EntryMeta) -> dict:
    return {
        "entry_id": entry_id,
        "title": entry.title,
        "url": entry.url,
        "source": entry.source,
        "timestamp": entry.timestamp.isoformat(),
        "summary": meta.llm_summary,
        "tags": meta.tags,
        "relevance_score": meta.relevance_score,
    }


# ── Source crawling ──────────────────────────────────────────────────────────

@mcp.tool()
def fetch_sources() -> str:
    """Crawl configured sources (Hacker News) and return raw entries as JSON.

    Returns a JSON array of raw entries, each with: source, url, title,
    raw_content, author, timestamp. These are NOT yet processed by an LLM —
    use get_harness_prompt to get processing instructions, then store_entry
    to save the results.
    """
    from aperture.source.hn import fetch_top_stories

    stories = asyncio.run(fetch_top_stories(settings.hn_top_n))
    return json.dumps(
        [s.model_dump(mode="json") for s in stories],
        indent=2,
    )


# ── Harness prompts ─────────────────────────────────────────────────────────

_HARNESS_SYSTEM = """\
You are a research assistant that processes technical articles for a deep learning \
test development engineer. Your job is to extract structured metadata from articles.

The user's interests: {interests}

For EACH article provided, respond with a JSON object containing:
- "llm_summary": A concise 2-3 sentence summary focusing on what is new or notable.
- "tags": A list of 3-7 lowercase tags describing the key topics. Use specific technical \
terms (e.g. "kv-cache", "flash-attention", "nccl") rather than vague ones (e.g. "technology").
- "relevance_score": A float 0.0-1.0 indicating how relevant this is to the user's interests. \
0.0 = completely irrelevant, 1.0 = directly about their core work.

Respond with ONLY valid JSON (no markdown fencing).\
"""

_HARNESS_USER = """\
Title: {title}
Source: {source}
Author: {author}

Content:
{content}\
"""


@mcp.tool()
def get_harness_prompt(title: str = "", source: str = "", author: str = "", content: str = "") -> str:
    """Get the harness prompt for LLM processing of a raw entry.

    If no arguments are provided, returns the system prompt template.
    If arguments are provided, returns both the system prompt and a
    formatted user prompt ready to send to any LLM.

    Args:
        title: Article title (optional)
        source: Source name e.g. "hackernews" (optional)
        author: Author name (optional)
        content: Article content, will be truncated to 4000 chars (optional)
    """
    system = _HARNESS_SYSTEM.format(interests=", ".join(settings.user_interests))

    if not title and not content:
        return json.dumps({
            "system_prompt": system,
            "user_prompt_template": _HARNESS_USER,
            "expected_response_format": {
                "llm_summary": "string",
                "tags": ["string"],
                "relevance_score": "float 0.0-1.0",
            },
            "relevance_threshold": settings.relevance_threshold,
        }, indent=2)

    user_msg = _HARNESS_USER.format(
        title=title,
        source=source,
        author=author,
        content=content[:4000],
    )
    return json.dumps({
        "system_prompt": system,
        "user_prompt": user_msg,
        "expected_response_format": {
            "llm_summary": "string",
            "tags": ["string"],
            "relevance_score": "float 0.0-1.0",
        },
        "relevance_threshold": settings.relevance_threshold,
    }, indent=2)


# ── Storage ──────────────────────────────────────────────────────────────────

@mcp.tool()
def store_entry(
    url: str,
    title: str,
    raw_content: str,
    source: str,
    llm_summary: str,
    tags: list[str],
    relevance_score: float,
    author: str = "",
    timestamp: str = "",
) -> str:
    """Store a processed entry in the knowledge base.

    Call this after using the harness prompt to process a raw entry through
    your LLM. Provide both the raw fields and the LLM-generated metadata.

    Args:
        url: Original article URL
        title: Article title
        raw_content: Original article content
        source: Source name (e.g. "hackernews", "twitter", "wechat")
        llm_summary: LLM-generated summary
        tags: LLM-generated tags
        relevance_score: LLM-generated relevance score (0.0-1.0)
        author: Article author (optional)
        timestamp: ISO timestamp (optional, defaults to now)
    """
    from aperture.store.json_store import _save_entry_sync

    ts = datetime.fromisoformat(timestamp) if timestamp else datetime.now(timezone.utc)
    entry = RawEntry(
        timestamp=ts,
        source=source,  # type: ignore[arg-type]
        url=url,
        title=title,
        raw_content=raw_content,
        author=author,
    )
    meta = EntryMeta(
        llm_summary=llm_summary,
        tags=tags,
        relevance_score=relevance_score,
    )

    entry_id = _save_entry_sync(entry, meta)
    return json.dumps({"status": "stored", "entry_id": entry_id})


@mcp.tool()
def store_feedback(entry_id: str, action: str) -> str:
    """Record human feedback on an entry.

    Args:
        entry_id: Entry ID in format 'YYYY-MM-DD/NNN'
        action: One of 'useful', 'not_useful', 'wrong'
    """
    from aperture.store.json_store import _append_feedback_sync

    from aperture.models import FeedbackRecord

    record = FeedbackRecord(
        entry_id=entry_id,
        action=action,  # type: ignore[arg-type]
    )
    _append_feedback_sync(record)
    return json.dumps({"status": "recorded", "entry_id": entry_id, "action": action})


# ── Query tools ──────────────────────────────────────────────────────────────

@mcp.tool()
def search_knowledge(query: str, limit: int = 10) -> str:
    """Search the knowledge base by keyword. Matches against titles, summaries, and tags.

    Args:
        query: Search terms (matched against title, summary, and tags)
        limit: Maximum number of results to return
    """
    query_lower = query.lower()
    entries = _load_entries(days=30)

    scored = []
    for entry_id, entry, meta in entries:
        searchable = f"{entry.title} {meta.llm_summary} {' '.join(meta.tags)}".lower()
        words = query_lower.split()
        hits = sum(1 for w in words if w in searchable)
        if hits > 0:
            scored.append((hits, meta.relevance_score, entry_id, entry, meta))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    results = [_entry_to_dict(eid, e, m) for _, _, eid, e, m in scored[:limit]]

    if not results:
        return f"No entries found matching '{query}'. The knowledge base has {len(entries)} entries from the last 30 days."
    return json.dumps(results, indent=2)


@mcp.tool()
def get_recent_entries(days: int = 7, limit: int = 20) -> str:
    """Get the most recent entries from the knowledge base.

    Args:
        days: How many days back to look
        limit: Maximum number of entries to return
    """
    entries = _load_entries(days=days)
    entries.sort(key=lambda x: x[2].relevance_score, reverse=True)
    results = [_entry_to_dict(eid, e, m) for eid, e, m in entries[:limit]]
    return json.dumps(results, indent=2)


@mcp.tool()
def get_entry(entry_id: str) -> str:
    """Get full details of a specific entry, including raw content.

    Args:
        entry_id: Entry ID in format 'YYYY-MM-DD/NNN' (e.g. '2026-03-22/001')
    """
    entries_dir = _entries_dir()
    parts = entry_id.split("/")
    if len(parts) != 2:
        return f"Invalid entry_id format: '{entry_id}'. Expected 'YYYY-MM-DD/NNN'."

    day, num = parts
    entry_path = entries_dir / day / f"{num}.json"
    meta_path = entries_dir / day / f"{num}.meta.json"

    if not entry_path.exists():
        return f"Entry '{entry_id}' not found."

    entry = RawEntry.model_validate_json(entry_path.read_text(encoding="utf-8"))
    result = {
        "entry_id": entry_id,
        "title": entry.title,
        "url": entry.url,
        "source": entry.source,
        "author": entry.author,
        "timestamp": entry.timestamp.isoformat(),
        "raw_content": entry.raw_content,
    }

    if meta_path.exists():
        meta = EntryMeta.model_validate_json(meta_path.read_text(encoding="utf-8"))
        result["summary"] = meta.llm_summary
        result["tags"] = meta.tags
        result["relevance_score"] = meta.relevance_score

    return json.dumps(result, indent=2)


@mcp.tool()
def list_tags(days: int = 30) -> str:
    """List all tags in the knowledge base with their frequency.

    Args:
        days: How many days back to look
    """
    entries = _load_entries(days=days)
    tag_counts: dict[str, int] = {}
    for _, _, meta in entries:
        for tag in meta.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    return json.dumps(dict(sorted_tags), indent=2)
