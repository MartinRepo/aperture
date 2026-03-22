"""LLM processing pipeline — summarize, tag, and score relevance."""

from __future__ import annotations

import json
import logging

import anthropic

from aperture.config import settings
from aperture.models import EntryMeta, RawEntry

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


SYSTEM_PROMPT = """\
You are a research assistant that processes technical articles for a deep learning \
test development engineer. Your job is to extract structured metadata from articles.

The user's interests: {interests}

Respond with ONLY a JSON object (no markdown fencing) with these fields:
- "llm_summary": A concise 2-3 sentence summary focusing on what is new or notable.
- "tags": A list of 3-7 lowercase tags describing the key topics. Use specific technical \
terms (e.g. "kv-cache", "flash-attention", "nccl") rather than vague ones (e.g. "technology").
- "relevance_score": A float 0.0-1.0 indicating how relevant this is to the user's interests. \
0.0 = completely irrelevant, 1.0 = directly about their core work.\
"""

USER_PROMPT = """\
Title: {title}
Source: {source}
Author: {author}

Content:
{content}\
"""


async def process_entry(entry: RawEntry) -> EntryMeta:
    """Send a raw entry through the LLM and return structured metadata."""
    client = _get_client()

    # Truncate content to stay within reasonable token limits
    content = entry.raw_content[:4000]

    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SYSTEM_PROMPT.format(interests=", ".join(settings.user_interests)),
        messages=[
            {
                "role": "user",
                "content": USER_PROMPT.format(
                    title=entry.title,
                    source=entry.source,
                    author=entry.author,
                    content=content,
                ),
            }
        ],
    )

    raw_text = message.content[0].text.strip()

    # Parse LLM response — handle possible markdown fencing
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        data = json.loads(raw_text)
        return EntryMeta(
            llm_summary=data["llm_summary"],
            tags=data["tags"],
            relevance_score=float(data["relevance_score"]),
        )
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error("Failed to parse LLM response: %s\nRaw: %s", e, raw_text)
        # Return a safe fallback so the pipeline doesn't break
        return EntryMeta(
            llm_summary=f"[Parse error] {entry.title}",
            tags=["parse-error"],
            relevance_score=0.5,
        )
