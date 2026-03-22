"""Hacker News crawler using the official Firebase API."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from aperture.models import RawEntry

logger = logging.getLogger(__name__)

HN_API = "https://hacker-news.firebaseio.com/v0"
SKIP_PREFIXES = ("Ask HN: Who is hiring", "Ask HN: Freelancer?")


async def _fetch_item(client: httpx.AsyncClient, item_id: int) -> dict | None:
    try:
        resp = await client.get(f"{HN_API}/item/{item_id}.json")
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, ValueError):
        logger.warning("Failed to fetch HN item %d", item_id)
        return None


async def _fetch_page_text(client: httpx.AsyncClient, url: str) -> str:
    """Best-effort fetch of the linked page. Returns empty string on failure."""
    try:
        resp = await client.get(url, follow_redirects=True, timeout=10.0)
        resp.raise_for_status()
        # Return raw text — LLM can handle messy HTML/text.
        # Truncate to avoid blowing up context.
        return resp.text[:5000]
    except Exception:
        return ""


def _should_skip(item: dict) -> bool:
    title = item.get("title", "")
    return any(title.startswith(p) for p in SKIP_PREFIXES)


async def fetch_top_stories(n: int = 30) -> list[RawEntry]:
    """Fetch the top N stories from Hacker News."""
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(f"{HN_API}/topstories.json")
        resp.raise_for_status()
        story_ids: list[int] = resp.json()[:n]

        # Fetch items concurrently with a semaphore to be polite
        sem = asyncio.Semaphore(10)

        async def fetch_with_limit(sid: int) -> dict | None:
            async with sem:
                return await _fetch_item(client, sid)

        items = await asyncio.gather(*[fetch_with_limit(sid) for sid in story_ids])

        entries: list[RawEntry] = []
        for item in items:
            if item is None or item.get("type") != "story" or _should_skip(item):
                continue

            url = item.get("url", f"https://news.ycombinator.com/item?id={item['id']}")
            title = item.get("title", "")

            # Fetch linked page content for richer LLM processing
            page_text = ""
            if item.get("url"):
                async with sem:
                    page_text = await _fetch_page_text(client, item["url"])

            raw_content = f"{title}\n\n{page_text}" if page_text else title

            entries.append(
                RawEntry(
                    timestamp=datetime.fromtimestamp(
                        item.get("time", 0), tz=timezone.utc
                    ),
                    source="hackernews",
                    url=url,
                    title=title,
                    raw_content=raw_content,
                    author=item.get("by", ""),
                    hn_score=item.get("score"),
                )
            )

        logger.info("Fetched %d stories from HN", len(entries))
        return entries
