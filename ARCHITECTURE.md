# Aperture — Personal Knowledge Base with LLM-Powered Information Pipeline

## Vision

Reduce information asymmetry by automatically collecting, processing, and delivering relevant technical content to a single Discord interface. The system acts as a personal research assistant that learns what you care about over time.

## Core Principles

1. **LLM is an index, not the source of truth** — raw content is always preserved; LLM outputs are disposable and regenerable.
2. **Append-only, never mutate** — entries and corrections are only added, never silently overwritten.
3. **Don't pre-organize, query on demand** — no rigid folder hierarchy; tags are multi-label and evolve; "views" are generated at read-time.
4. **Feedback must be effortless** — one-tap buttons on Discord, not forms or text input.
5. **Start minimal, grow incrementally** — prove the core loop before adding sources or features.

---

## Architecture Overview

```
INPUT LAYER          PROCESSING LAYER         KNOWLEDGE BASE         DISCORD LAYER
┌──────────┐        ┌──────────────────┐     ┌────────────────┐    ┌──────────────┐
│  WeChat   │──┐    │ LLM Pipeline     │     │ Layer 1: Raw   │    │ #daily-digest│
│  HN       │──┼──▶ │ Summarize        │──▶  │ Layer 2: Meta  │──▶ │ #feed        │
│  Twitter  │──┘    │ Tag + Verify     │     │ Corrections/   │◀── │ #ask         │
│  (future) │       │ Score relevance  │     │ User profile   │    │ [buttons]    │
└──────────┘        └──────────────────┘     └────────────────┘    └──────────────┘
                                                                     ▲        │
                                                                     │feedback │
                                                                     └────────┘
```

---

## Knowledge Base Design (3 Layers)

### Layer 1: Append-only log (the truth)

Each entry is a timestamped JSON file. Never modified after creation.

```
/entries/2026-03-22/001.json
{
  "timestamp": "2026-03-22T08:30:00Z",
  "source": "hackernews",
  "url": "https://...",
  "title": "...",
  "raw_content": "...",
  "author": "..."
}
```

### Layer 2: LLM-generated metadata (the associations)

Stored alongside the entry. Can be regenerated at any time.

```
/entries/2026-03-22/001.meta.json
{
  "llm_summary": "...",
  "facts": [
    "PyTorch 2.5 added torch.compile support for custom CUDA kernels",
    "Performance improvement: 2.3x on A100 for tested workloads"
  ],
  "interpretations": [
    "May affect custom op test coverage in existing test frameworks"
  ],
  "tags": ["pytorch", "torch-compile", "cuda-kernels", "performance"],
  "tag_evidence": {
    "pytorch": "quoted sentence from source...",
    "torch-compile": "quoted sentence from source..."
  },
  "confidence": 0.87,
  "relevance_score": 0.92
}
```

### Layer 3: On-demand views (the intelligence)

No stored files. Generated at query time when a user asks a question in `#ask`. The LLM searches Layer 1+2 by tags and semantic similarity, then synthesizes an answer with source links.

### Corrections log

Append-only human feedback from Discord button interactions.

```
/corrections/2026-03-22.jsonl
{"entry": "001", "action": "not_useful", "timestamp": "..."}
{"entry": "003", "action": "wrong", "field": "llm_summary", "timestamp": "..."}
```

### User profile

Interests and learned preferences, updated by feedback loop.

```
/user_profile.json
{
  "interests": ["deep-learning", "cuda", "test-infrastructure", "inference"],
  "tag_weights": { "kv-cache": 1.4, "frontend-css": 0.1 },
  "feedback_history_ref": "/corrections/"
}
```

---

## LLM Reliability Model

| Risk | Mitigation |
|---|---|
| Summary misses key point | Raw content always preserved; summary links to source |
| Hallucinated claim in summary | Facts extracted with quotes; interpretations labeled separately |
| Wrong tags | Self-verification: LLM must quote evidence per tag, drop unverifiable tags |
| Bad query synthesis | Responses include source links; user can click through to verify |
| Drift over time | User feedback buttons tune relevance; corrections log tracks errors |

---

## Discord Interface

### Apertures

| Channel | Trigger | Purpose |
|---|---|---|
| `#daily-digest` | Scheduled (morning) | Curated briefing, 5-10 min read, grouped by theme |
| `#feed` | Real-time | High-relevance items only, pushed immediately |
| `#ask` | On-demand | User queries the knowledge base ("what do I know about KV cache?") |

### Digest entry format

```
[DL/Inference] FlashAttention-3 benchmark on H200     🔴 High relevance

Facts:
• FlashAttention-3 achieves 2.1x speedup on H200 vs H100
• Supports variable-length sequences natively

Interpretation:
• May require test matrix update for new attention kernels

Source: https://...
[Useful] [Not Useful] [Wrong]
```

### Feedback buttons

- **[Useful]** — positive signal, increases weight of related tags in user profile
- **[Not Useful]** — negative signal, decreases weight
- **[Wrong]** — logs a correction, flags entry for review

---

## Input Sources

### Hacker News
- Official API (free, reliable, no auth needed)
- Poll top/new stories on a schedule

### Twitter
- RSSHub or Nitter instance to avoid API costs
- Follow specific accounts/lists relevant to DL and systems

### WeChat
- **Phase 1 approach: share-to-Discord.** User shares articles from WeChat to a Discord channel; the bot picks them up and processes them. One extra tap, 100% reliable.
- Future: explore RSSHub for WeChat public accounts, or wechaty (with account ban risk caveat)

---

## Tech Stack

```
Runtime:        Python or Node.js (TBD)
LLM:            Claude API
                  - Haiku: tagging, self-verification (cheap, fast)
                  - Sonnet: summarization, query synthesis
Discord:        discord.js or discord.py
Crawlers:       Source-specific (HN API, RSSHub for Twitter)
Storage:        Local JSON files, git-tracked
Scheduler:      Cron or in-process scheduler
```

---

## Phased Build Plan

### Phase 1 — Core loop
- HN crawler
- LLM processing pipeline (summarize → tag → store)
- Discord bot with `#daily-digest`
- `[Useful]` / `[Not Useful]` buttons
- File-based knowledge base

### Phase 2 — Reliability + query
- Fact vs interpretation separation in processing
- Tag self-verification with evidence
- `#ask` channel with knowledge base query
- Corrections logging

### Phase 3 — More sources + learning
- Twitter crawler via RSSHub
- WeChat share-to-Discord flow
- User profile learning from feedback history
- `#feed` channel for real-time high-relevance items

### Phase 4 — Remote access
- Claude Code Remote Control integration
- Deep-dive queries from phone/tablet via Claude app
- Cross-reference and synthesis across knowledge base
