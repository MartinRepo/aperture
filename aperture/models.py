from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class RawEntry(BaseModel):
    """A single piece of raw content from any source."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: Literal["hackernews", "twitter", "wechat"]
    url: str
    title: str
    raw_content: str
    author: str = ""
    hn_score: int | None = None


class EntryMeta(BaseModel):
    """LLM-generated metadata for a RawEntry. Disposable and regenerable."""

    llm_summary: str
    tags: list[str]
    relevance_score: float = Field(ge=0.0, le=1.0)


class FeedbackRecord(BaseModel):
    """A single human feedback action from Discord."""

    entry_id: str  # e.g. "2026-03-22/001"
    action: Literal["useful", "not_useful", "wrong"]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
