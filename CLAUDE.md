# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

**Aperture** is a personal knowledge base with an LLM-powered information pipeline. It collects technical content from sources (Hacker News, Twitter, WeChat), processes it through Claude API (summarize, tag, score relevance), stores it as local JSON files, and delivers digests to a Discord bot with feedback buttons.

## Commands

```bash
# Setup (uses uv for package management)
uv venv && uv pip install -e "."

# Full pipeline: fetch → process → store → post to Discord
uv run python -m aperture.main

# Fetch and process only (no Discord)
uv run python -m aperture.main fetch

# Post existing entries to Discord only
uv run python -m aperture.main post
```

## Architecture

Four components connected in a linear pipeline: **Source → Processor → Store → Delivery**

- `aperture/source/hn.py` — HN Firebase API crawler via httpx
- `aperture/processor/summarize.py` — Claude Haiku: summarize + tag + relevance score in one call
- `aperture/store/json_store.py` — Append-only JSON files under `data/entries/YYYY-MM-DD/`
- `aperture/delivery/discord_bot.py` — Discord embeds with Useful/Not Useful/Wrong feedback buttons
- `aperture/models.py` — Three Pydantic models: `RawEntry`, `EntryMeta`, `FeedbackRecord`
- `aperture/config.py` — pydantic-settings loading from `.env`

## Key design principles

- **LLM is an index, not the source of truth** — raw content always preserved alongside LLM-generated metadata (.json + .meta.json pairs). LLM outputs are disposable and regenerable.
- **No abstract base classes** — concrete implementations only. Extract interfaces when a second implementation exists, not before.
- **Append-only** — entries and corrections are never silently modified. Feedback goes to `data/corrections/YYYY-MM-DD.jsonl`.
- **Flat storage** — no nested category directories. Tags are multi-label. "Views" are generated at query time.

## Configuration

All config via `.env` (see `.env.example`). Key settings in `aperture/config.py`:
- `ANTHROPIC_API_KEY`, `DISCORD_TOKEN`, `DISCORD_CHANNEL_ID` — required
- `HN_TOP_N` (default 30), `RELEVANCE_THRESHOLD` (default 0.5)
- `user_interests` list drives LLM relevance scoring
