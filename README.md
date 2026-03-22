# Aperture

> Control exactly how much information gets through.

Aperture is a personal knowledge base powered by an LLM pipeline. It collects technical content from Hacker News, Twitter, and WeChat — filters it by relevance to your interests, summarizes it, tags it, and delivers a daily digest straight to Discord. One inbox. No noise.

---

## The problem it solves

The internet produces more signal than any one person can process. For engineers in fast-moving fields, this creates a real cost: missing an important paper, a breaking API change, or a technique your peers already know. Aperture is built to close that gap — quietly, every day, without becoming another tool you have to maintain.

---

## How it works

```
  Sources                 LLM Pipeline              Knowledge Base          Discord
┌──────────┐           ┌───────────────┐           ┌──────────────┐      ┌──────────────┐
│ Hacker   │           │  Summarize    │           │  Raw entry   │      │ #daily-digest│
│   News   │──────────▶│  Tag          │──────────▶│  + metadata  │─────▶│ #feed        │
│ Twitter  │           │  Score        │           │  Corrections │◀─────│ #ask         │
│  WeChat  │           └───────────────┘           │  User profile│      │  [buttons]   │
└──────────┘                                       └──────────────┘      └──────────────┘
```

Each article passes through three steps:

1. **Summarize** — Claude extracts a tight 2-3 sentence summary, separating facts from interpretations
2. **Tag** — multi-label tags with evidence quotes (if Claude can't cite a source sentence, the tag is dropped)
3. **Score** — a 0–1 relevance score against your personal interest profile

Only entries above your relevance threshold reach Discord. Everything below is still stored — just silently.

---

## Discord interface

Aperture has one human-facing surface: Discord.

| Channel | When | What |
|---|---|---|
| `#daily-digest` | Morning, scheduled | Curated briefing sorted by relevance. One embed per entry, with feedback buttons. |
| `#feed` | Real-time | High-relevance items pushed immediately as they're processed. |
| `#ask` | On-demand | Ask anything — "what do I know about KV cache?" — and Aperture queries the knowledge base and synthesizes an answer with source links. |

Each digest embed looks like this:

```
🔴  FlashAttention-3 benchmark results on H200

FlashAttention-3 achieves a 2.1x throughput improvement over FA2 on H100/H200
by exploiting async execution between TMA and WGMMA instructions. The technique
generalizes to variable-length sequences and FP8 quantization.

Tags:  `flash-attention`  `cuda`  `inference`  `attention`     Relevance: 94%

                              [ Useful ]  [ Not Useful ]  [ Wrong ]
```

Clicking **Useful** or **Not Useful** takes one tap and updates your relevance model. **Wrong** logs a correction for review — nothing is silently overwritten.

---

## Knowledge base design

Aperture stores everything in flat JSON files on your local machine — no database, no migration scripts.

```
data/
├── entries/
│   └── 2026-03-22/
│       ├── 001.json          ← raw content, always preserved
│       ├── 001.meta.json     ← LLM output, disposable and regenerable
│       └── ...
├── corrections/
│   └── 2026-03-22.jsonl      ← append-only feedback log
└── user_profile.json         ← interests + learned tag weights
```

**The raw entry is the source of truth. The LLM output is an index.** If every summary were wrong, you'd re-run the processor. The underlying content is untouched.

There are no directories by topic. Tags are multi-label and evolve as your interests do. "Views" — weekly summaries, topic briefs, cross-article connections — are generated at query time, not stored.

---

## Reliability

LLMs make mistakes. Aperture is designed around this fact:

| Where it can go wrong | What Aperture does |
|---|---|
| Summary misses the point | Raw content always preserved; one click to the source |
| Hallucinated claim | Facts and interpretations are labeled separately |
| Wrong tag | LLM must quote source evidence per tag; unverifiable tags are dropped |
| Bad synthesis in `#ask` | Every response includes source links for verification |
| Relevance drift | Feedback buttons retrain the relevance model over time |

---

## Setup

**Requirements:** Python 3.11+, [uv](https://github.com/astral-sh/uv), an Anthropic API key, a Discord bot token.

```bash
# 1. Clone and install
git clone <repo>
cd channel
uv venv && uv pip install -e "."

# 2. Configure
cp .env.example .env
# Fill in ANTHROPIC_API_KEY, DISCORD_TOKEN, DISCORD_CHANNEL_ID

# 3. Run
uv run python -m aperture.main
```

**Optional:** tune your interest profile in `aperture/config.py` before the first run:

```python
user_interests: list[str] = [
    "deep-learning", "cuda", "inference", "pytorch", "test-infrastructure", ...
]
```

---

## Commands

```bash
uv run python -m aperture.main          # full pipeline: fetch → process → store → post
uv run python -m aperture.main fetch    # pipeline only, no Discord (test your API key)
uv run python -m aperture.main post     # post today's already-processed entries to Discord
```

---

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| LLM | Claude Haiku (process) via [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) |
| Discord | [discord.py](https://github.com/Rapptz/discord.py) |
| HTTP | [httpx](https://github.com/encode/httpx) |
| Models | [Pydantic](https://docs.pydantic.dev/) v2 |
| Storage | Local JSON files |

---

## Roadmap

- [x] Phase 1 — HN crawler, LLM pipeline, Discord digest, feedback buttons
- [ ] Phase 2 — Fact/interpretation split, tag self-verification, `#ask` channel
- [ ] Phase 3 — Twitter (RSSHub), WeChat share-to-Discord, relevance learning from feedback
- [ ] Phase 4 — Claude Code Remote Control integration for mobile deep-dives

---

## Philosophy

Aperture is deliberately small. It has no web UI, no database, no plugin system. It does one thing: move the right information to you, every day, with minimal friction. Complexity is added only when a real need appears — not in anticipation of one.
