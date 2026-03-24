# Aperture — Personal Knowledge Harness

## Vision

Reduce information asymmetry by providing a curated, verified knowledge base that both humans and AI agents can consume. Aperture is a **knowledge harness** — it owns the sources, the storage, and the processing rules, but delegates LLM inference and human delivery to an external orchestrator (OpenClaw/NemoClaw).

## Core Principles

1. **LLM is an index, not the source of truth** — raw content is always preserved; LLM outputs are disposable and regenerable.
2. **No API keys** — Aperture provides harness prompts; the orchestrator handles LLM access through whatever the user already has.
3. **Append-only, never mutate** — entries and corrections are only added, never silently overwritten.
4. **Don't pre-organize, query on demand** — no rigid folder hierarchy; tags are multi-label and evolve; "views" are generated at read-time.
5. **Knowledge harness first** — the primary consumers are AI agents; the knowledge base must be correct enough for agents to act on blindly.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│              OpenClaw / NemoClaw                 │
│                                                  │
│  LLM access (any model the user has)             │
│  Telegram interface (native)                     │
│  Orchestration: fetch → process → store → post   │
└────────────────────┬────────────────────────────┘
                     │ MCP
                     ▼
┌─────────────────────────────────────────────────┐
│                  Aperture                        │
│              (pure MCP server)                   │
│                                                  │
│  Source crawlers ─── fetch_sources               │
│  Harness prompts ── get_harness_prompt           │
│  Storage ────────── store_entry, store_feedback  │
│  Query ──────────── search_knowledge,            │
│                     get_recent_entries,           │
│                     get_entry, list_tags          │
└─────────────────────────────────────────────────┘
```

The orchestrator (OpenClaw) calls Aperture's MCP tools in sequence:

1. `fetch_sources` → get raw articles from HN
2. `get_harness_prompt(title, content, ...)` → get processing prompt
3. Send prompt to LLM (via OpenClaw's own LLM access)
4. `store_entry(raw + LLM output)` → save to knowledge base
5. Deliver digest via Telegram (OpenClaw's native capability)

Claude Code and other agents can also query the knowledge base directly via `search_knowledge`, `get_recent_entries`, etc.

---

## MCP Tools (8 total)

### Source crawling

| Tool | Description |
|---|---|
| `fetch_sources()` | Crawl HN top stories, return raw entries as JSON |

### LLM harness

| Tool | Description |
|---|---|
| `get_harness_prompt(title?, content?, ...)` | Return system + user prompt for LLM processing. With no args, returns the template. With args, returns a ready-to-send prompt. |
| `store_entry(url, title, raw_content, source, llm_summary, tags, relevance_score, ...)` | Save a processed entry (raw + metadata) to the knowledge base |
| `store_feedback(entry_id, action)` | Record human feedback: useful, not_useful, or wrong |

### Knowledge query

| Tool | Description |
|---|---|
| `search_knowledge(query, limit)` | Keyword search across titles, summaries, and tags |
| `get_recent_entries(days, limit)` | Most recent entries sorted by relevance score |
| `get_entry(entry_id)` | Full details of a single entry including raw content |
| `list_tags(days)` | Tag frequency map across the knowledge base |

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
  "tags": ["pytorch", "torch-compile", "cuda-kernels"],
  "relevance_score": 0.92
}
```

### Layer 3: On-demand views (the intelligence)

No stored files. Generated at query time via `search_knowledge` or `get_recent_entries`. The querying agent (or OpenClaw) synthesizes answers from returned entries.

### Corrections log

Append-only human feedback from Telegram (via OpenClaw → `store_feedback`).

```
/corrections/2026-03-22.jsonl
{"entry_id": "2026-03-22/001", "action": "not_useful", "timestamp": "..."}
```

---

## LLM Reliability Model

| Risk | Mitigation |
|---|---|
| Summary misses key point | Raw content always preserved; summary links to source |
| Hallucinated claim | Harness prompt instructs fact extraction; raw content verifiable |
| Wrong tags | Harness prompt enforces specific technical terms over vague ones |
| Bad query synthesis | MCP responses include source URLs; agents can verify |
| Drift over time | Feedback via `store_feedback` tracks errors over time |
| Agent acts on bad data | All MCP responses include relevance scores and source URLs |

---

## Input Sources

### Hacker News (implemented)
- Official API (free, reliable, no auth needed)
- Fetched via `fetch_sources` tool

### Twitter (planned)
- RSSHub or Nitter instance to avoid API costs
- Follow specific accounts/lists relevant to DL and systems

### WeChat (planned)
- Share-to-Telegram flow: user shares article from WeChat to Telegram, OpenClaw picks it up and calls `store_entry`

---

## Tech Stack

```
Runtime:        Python 3.11+
Package mgr:    uv
Protocol:       MCP (via mcp Python SDK)
HTTP:           httpx (for source crawling)
Models:         Pydantic v2
Storage:        Local JSON files
Orchestrator:   OpenClaw / NemoClaw (external)
LLM:            Whatever the orchestrator has access to (no API keys in Aperture)
Telegram:       Handled by OpenClaw (native)
```

---

## Phased Build Plan

### Phase 1 — Core harness (done)
- HN crawler via `fetch_sources`
- Harness prompts via `get_harness_prompt`
- Knowledge base storage via `store_entry`
- Feedback recording via `store_feedback`
- Query tools: `search_knowledge`, `get_recent_entries`, `get_entry`, `list_tags`
- MCP server as sole interface

### Phase 2 — Reliability + richer prompts
- Fact vs interpretation separation in harness prompt
- Tag self-verification with evidence quotes
- Confidence scoring in metadata

### Phase 3 — More sources
- Twitter crawler added to `fetch_sources`
- WeChat share-to-Telegram flow via OpenClaw

### Phase 4 — Advanced harness
- Semantic search (embeddings) for MCP queries
- Agent-generated KNOWLEDGE.md context files for projects
- Cross-reference and synthesis across entries
