# Aperture

> Control exactly how much information gets through.

Aperture is a **knowledge harness** — a pure MCP server that crawls technical content, provides structured prompts for LLM processing, stores results in a local knowledge base, and exposes search/query tools for AI agents.

It owns **no LLM API keys** and **no messaging bot**. LLM inference and human delivery (Telegram) are handled by an external orchestrator like [OpenClaw](https://github.com/openclaw/openclaw) / [NemoClaw](https://nvidianews.nvidia.com/news/nvidia-announces-nemoclaw). Aperture focuses on what it does best: reliable source crawling, harness prompts, and structured knowledge storage.

---

## Why this exists

The internet produces more signal than any one person can process. For engineers in fast-moving fields, this creates a real cost: missing an important paper, a breaking API change, or a technique your peers already know.

But it's not just humans who need good context — **AI agents do too.** An agent working with stale or hallucinated knowledge makes bad decisions. Aperture is both a personal briefing system and a knowledge harness that ensures agents have correct, up-to-date context to act on.

**No API keys needed.** Most engineers at companies like NVIDIA, Google, or Meta have LLM access through company accounts or internal tooling — not raw API keys. Aperture works with whatever LLM access your orchestrator provides.

---

## How it works

```
┌─────────────────────────────────────────────┐
│           OpenClaw / NemoClaw               │
│                                             │
│  Your LLM access (any model)               │
│  Telegram (built-in)                        │
│  Orchestration: fetch → process → deliver   │
└──────────────────┬──────────────────────────┘
                   │ MCP
                   ▼
┌─────────────────────────────────────────────┐
│              Aperture                       │
│          (pure MCP server)                  │
│                                             │
│  Source crawlers    Knowledge base           │
│  Harness prompts    Search & query          │
└─────────────────────────────────────────────┘
```

The orchestrator calls Aperture's tools in sequence:

1. **`fetch_sources`** → crawl HN, get raw articles
2. **`get_harness_prompt`** → get the processing prompt for each article
3. Send to LLM (via orchestrator's own access)
4. **`store_entry`** → save raw content + LLM metadata to knowledge base
5. Deliver digest via Telegram (orchestrator's native capability)

Claude Code and other agents can also query the knowledge base directly.

---

## MCP tools (8)

### Source crawling
| Tool | What it does |
|---|---|
| `fetch_sources()` | Crawl HN top stories, return raw entries |

### LLM harness
| Tool | What it does |
|---|---|
| `get_harness_prompt(title?, content?)` | Return system + user prompt for LLM processing |
| `store_entry(url, title, raw_content, ...)` | Save processed entry to knowledge base |
| `store_feedback(entry_id, action)` | Record human feedback |

### Knowledge query
| Tool | What it does |
|---|---|
| `search_knowledge(query)` | Keyword search across titles, summaries, tags |
| `get_recent_entries(days)` | Latest entries ranked by relevance |
| `get_entry(entry_id)` | Full details including raw content |
| `list_tags(days)` | Tag frequency map |

---

## Knowledge base

Flat JSON files on your local machine — no database, no migration scripts.

```
data/
├── entries/
│   └── 2026-03-22/
│       ├── 001.json          ← raw content, always preserved
│       ├── 001.meta.json     ← LLM output, disposable and regenerable
│       └── ...
└── corrections/
    └── 2026-03-22.jsonl      ← append-only feedback log
```

**The raw entry is the source of truth. The LLM output is an index.** If every summary were wrong, you'd re-run the processor. The underlying content is untouched.

---

## Setup

**Requirements:** Python 3.11+, [uv](https://github.com/astral-sh/uv)

```bash
# 1. Clone and install
git clone <repo>
cd channel
uv venv && uv pip install -e "."

# 2. Configure (optional)
cp .env.example .env
# Tune HN_TOP_N, RELEVANCE_THRESHOLD, user_interests in aperture/config.py

# 3. Run
uv run python -m aperture.main
```

### Connecting to OpenClaw / NemoClaw

Add Aperture as an MCP server in your OpenClaw config.

### Connecting to Claude Code

Add to `~/.claude/settings.json` or project `.mcp.json`:

```json
{
  "mcpServers": {
    "aperture": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/aperture", "python", "-m", "aperture.main"]
    }
  }
}
```

---

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Package manager | [uv](https://github.com/astral-sh/uv) |
| Protocol | [MCP](https://modelcontextprotocol.io/) via `mcp` Python SDK |
| HTTP | [httpx](https://github.com/encode/httpx) |
| Models | [Pydantic](https://docs.pydantic.dev/) v2 |
| Storage | Local JSON files |
| Orchestrator | [OpenClaw](https://github.com/openclaw/openclaw) / [NemoClaw](https://nvidianews.nvidia.com/news/nvidia-announces-nemoclaw) (external) |

---

## Roadmap

- [x] Phase 1 — HN crawler, harness prompts, knowledge base, MCP server (8 tools)
- [ ] Phase 2 — Fact/interpretation split, tag self-verification, confidence scoring
- [ ] Phase 3 — Twitter (RSSHub), WeChat share-to-Telegram via OpenClaw
- [ ] Phase 4 — Semantic search, agent-generated KNOWLEDGE.md, cross-referencing

---

## Philosophy

Aperture is deliberately small. It has no web UI, no database, no LLM API keys, no messaging bot. It does one thing: maintain a reliable knowledge base that humans and agents can query. The orchestrator (OpenClaw) handles everything else. Complexity is added only when a real need appears — not in anticipation of one.
