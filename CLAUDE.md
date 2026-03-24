# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

**Aperture** is a personal knowledge harness exposed as an MCP server. It crawls technical content from sources (Hacker News, Twitter, WeChat), provides harness prompts for LLM processing, stores results as local JSON files, and exposes search/query tools. LLM processing and human delivery (Telegram) are handled by an external orchestrator like OpenClaw/NemoClaw — Aperture owns no LLM API keys and no messaging bot.

## Commands

```bash
# Setup (uses uv for package management)
uv venv && uv pip install -e "."

# Run the MCP server
uv run python -m aperture.main
```

## Architecture

Aperture is a **pure MCP server** with 8 tools in three groups:

**Source crawling:**
- `fetch_sources` — crawl HN (and future sources), return raw entries

**LLM harness:**
- `get_harness_prompt` — return system/user prompts for processing a raw entry
- `store_entry` — save a processed entry (raw + LLM metadata) to the KB
- `store_feedback` — record human feedback (useful/not_useful/wrong)

**Knowledge query:**
- `search_knowledge` — keyword search across titles, summaries, tags
- `get_recent_entries` — latest entries ranked by relevance
- `get_entry` — full details of a single entry including raw content
- `list_tags` — tag frequency map

## Key files

- `aperture/mcp_server.py` — All 8 MCP tools, harness prompts, and query logic
- `aperture/source/hn.py` — HN Firebase API crawler via httpx
- `aperture/store/json_store.py` — Append-only JSON files under `data/entries/YYYY-MM-DD/`
- `aperture/models.py` — Three Pydantic models: `RawEntry`, `EntryMeta`, `FeedbackRecord`
- `aperture/config.py` — pydantic-settings loading from `.env`

## Key design principles

- **LLM is an index, not the source of truth** — raw content always preserved alongside LLM-generated metadata (.json + .meta.json pairs). LLM outputs are disposable and regenerable.
- **No LLM API keys** — Aperture provides harness prompts; the orchestrator (OpenClaw) handles LLM access.
- **Append-only** — entries and corrections are never silently modified. Feedback goes to `data/corrections/YYYY-MM-DD.jsonl`.
- **Flat storage** — no nested category directories. Tags are multi-label. "Views" are generated at query time.

## Configuration

All config via `.env` (see `.env.example`). Key settings in `aperture/config.py`:
- `HN_TOP_N` (default 30), `RELEVANCE_THRESHOLD` (default 0.5)
- `user_interests` list drives harness prompt relevance scoring
