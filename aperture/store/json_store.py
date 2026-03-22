from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from aperture.config import settings
from aperture.models import EntryMeta, FeedbackRecord, RawEntry


def _today_dir() -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return settings.data_dir / "entries" / today


def _next_entry_number(day_dir: Path) -> int:
    """Find the next sequential entry number for the given day."""
    if not day_dir.exists():
        return 1
    existing = [
        f.stem
        for f in day_dir.glob("*.json")
        if not f.stem.endswith(".meta")
    ]
    if not existing:
        return 1
    numbers = [int(n) for n in existing if n.isdigit()]
    return max(numbers) + 1 if numbers else 1


def _save_entry_sync(entry: RawEntry, meta: EntryMeta) -> str:
    day_dir = _today_dir()
    day_dir.mkdir(parents=True, exist_ok=True)

    num = _next_entry_number(day_dir)
    entry_id = f"{day_dir.name}/{num:03d}"

    entry_path = day_dir / f"{num:03d}.json"
    meta_path = day_dir / f"{num:03d}.meta.json"

    entry_path.write_text(entry.model_dump_json(indent=2), encoding="utf-8")
    meta_path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")

    return entry_id


async def save_entry(entry: RawEntry, meta: EntryMeta) -> str:
    """Save raw entry and its LLM metadata. Returns entry_id like '2026-03-22/001'."""
    return await asyncio.to_thread(_save_entry_sync, entry, meta)


def _load_today_entries_sync() -> list[tuple[str, RawEntry, EntryMeta]]:
    day_dir = _today_dir()
    if not day_dir.exists():
        return []

    results = []
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


async def load_today_entries() -> list[tuple[str, RawEntry, EntryMeta]]:
    """Load all entries for today, sorted by entry number."""
    return await asyncio.to_thread(_load_today_entries_sync)


def _append_feedback_sync(record: FeedbackRecord) -> None:
    corrections_dir = settings.data_dir / "corrections"
    corrections_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = corrections_dir / f"{today}.jsonl"

    with open(path, "a", encoding="utf-8") as f:
        f.write(record.model_dump_json() + "\n")


async def append_feedback(record: FeedbackRecord) -> None:
    """Append a feedback record to today's corrections log."""
    await asyncio.to_thread(_append_feedback_sync, record)


async def entry_url_exists(url: str) -> bool:
    """Check if an entry with this URL already exists today (dedup)."""
    entries = await load_today_entries()
    return any(e.url == url for _, e, _ in entries)
