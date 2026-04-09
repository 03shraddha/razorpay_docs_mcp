# razorpay-docs-mcp

> **You're building a Razorpay integration at 2am. Your AI coding agent writes the webhook handler with confidence. It looks right. It runs. You ship it. Three days later, production starts silently dropping payments because the agent used a field name that Razorpay deprecated eight months ago — and it was never in the training data.**
>
> This is that fix.

---

## What this actually is

A **knowledge MCP server** — two tools, zero infrastructure, runs locally — that gives your AI coding agent (Claude Code, Cursor, Claude Desktop, Continue, Windsurf) direct, real-time access to Razorpay's official documentation. When your agent is about to write a Razorpay API call, it can now look it up first instead of guessing.

Two tools:
- **`search_razorpay_docs`** — BM25 full-text search across 2,200+ Razorpay docs. Returns ranked results with source URLs.
- **`get_razorpay_docs`** — Fetch the full markdown for any doc page by its canonical `razorpay.com/docs/...` URL.

Every result includes a citable `razorpay.com/docs/...` URL. The agent can show it to you, you can click it, and you can verify the answer came from Razorpay — not from a two-year-old Stack Overflow answer or a blog post that's half-wrong.

---

## Why this exists — the actual problem

AI coding agents are trained on a snapshot of the internet. That snapshot is at minimum 12 months old, often 18–24 months. Razorpay ships product updates continuously. The gap between "what the model knows" and "what Razorpay actually does right now" is where bugs live.

This isn't a hypothetical. It shows up as:
- Wrong field names in webhook payloads
- Deprecated authentication flows
- Payment capture logic that used to work but was changed with the recurring payments mandate
- UPI AutoPay setup steps that are missing a required parameter added six months ago
- Error codes that exist in prod but aren't in the model's training data

The model doesn't signal uncertainty on these. It writes the wrong code with the same confidence it writes correct code. You don't find out until something breaks in production.

This MCP is a dedicated, trusted channel that the agent is **told to consult** for Razorpay-specific questions. It short-circuits the guessing entirely.

---

## "But my agent can already do web search…"

Yes. Here's why that's not the same thing.

| Web search | This MCP |
|---|---|
| Agent doesn't know it needs to search. It only fires web search if it already suspects it might be wrong — but it usually doesn't. | Agent has an explicit, always-available channel for Razorpay questions. It checks docs the same way it checks type definitions. |
| Search returns a mix of blog posts, StackOverflow answers (some from 2019), competitor tutorials, and partial Razorpay pages. Agent has to judge which source is authoritative and frequently guesses wrong. | Every result comes from Razorpay's own official documentation, pre-indexed, ranked by relevance. Zero source ambiguity. |
| Web search on `razorpay webhook signature verification` returns 7 results with 4 different code patterns. One is from the correct current SDK. The agent picks one. | Search returns the specific chunk of the official doc with the correct current pattern and a citable URL. |
| Adds latency, consumes tokens on search result parsing, and still has no guarantee of accuracy. | Sub-100ms local BM25 lookup. No external API calls at query time. |
| Requires the agent to recognize it needs help. Agents don't ask for help on things they confidently think they know. | Runs as a registered tool the agent is instructed to use for Razorpay — removes the "do I need to look this up?" decision entirely. |

The core problem is not "can the agent find docs." It's that **the agent doesn't know it's wrong.** Web search only helps if the agent suspects it's wrong. This MCP makes correct Razorpay docs the path of least resistance, so the agent uses them whether or not it "thinks" it needs to.

---

## "Razorpay already has an MCP server. Why build another one?"

The existing [`razorpay-mcp-server`](https://github.com/razorpay/razorpay-mcp-server) is excellent and does something completely different.

| Razorpay's official MCP | This Docs MCP |
|---|---|
| **Actions** — 43 tools that execute real API calls: create orders, issue refunds, trigger payouts, manage settlements | **Knowledge** — 2 tools that answer questions about how to use the API |
| Talks to your live Razorpay account. Requires API keys. | Reads documentation locally. No API keys needed. |
| Built for: *"I want my agent to automate my Razorpay account"* | Built for: *"I want my agent to write correct Razorpay integration code"* |
| Solves: developer using an agent as a dashboard replacement | Solves: developer integrating Razorpay into their product for the first time |
| Your agent already needs to know the right API call before it uses this | Your agent reads this to figure out what the right API call is |

They are complementary. The action MCP needs you to already understand Razorpay. The docs MCP is what your agent reads to get there. Installing both is the correct setup — one tells the agent *what to do*, the other tells it *how to do it right*.

Without the docs MCP, you are handing a developer an action MCP and expecting them to know which of 43 tools to call, with what parameters, in what order. That's the knowledge vacuum the docs MCP fills.

---

## Common objections — Q&A

| Question | Answer |
|---|---|
| **"Razorpay's docs are already online. Why index them locally?"** | Because "online" means JS-rendered SPA pages that return empty HTML to any non-browser client. Razorpay actually publishes a machine-readable version at `razorpay.com/docs/llms.txt` — 2,200+ markdown files on GitHub. This MCP indexes that. It's faster, offline-capable, and returns clean structured results instead of raw HTML soup. |
| **"Won't this go stale?"** | Run `python -m razorpay_docs_mcp.refresh` to re-index. It pulls fresh from Razorpay's own GitHub (`llms.txt` links), re-indexes in under 5 minutes, and replaces the old data. You control when to refresh — before a big integration, after a Razorpay changelog, whenever. No background jobs, no cron, no subscriptions. |
| **"What if the docs themselves have errors?"** | Then you get the official error, not a hallucinated error. That's strictly better — the source URL is right there, your team can file a docs bug with Razorpay, and you're not debugging phantom behavior that exists only in your agent's training data. |
| **"Isn't 2,200 docs too much to search accurately?"** | BM25 is designed for exactly this scale. It's the same algorithm powering Elasticsearch and Solr. DuckDB's FTS extension indexes all 20,000+ chunks and returns results in under 100ms. The `product` filter lets you narrow to just `webhooks`, `api`, `payments`, etc. if you want tighter results. |
| **"Does the agent use this automatically or do I have to prompt it?"** | Once registered as an MCP server, the agent sees it as an available tool. For agents that support system prompts or tool instructions (Claude Code, Cursor), you can add one line — "Use the razorpay-docs MCP for any Razorpay-related questions" — and it happens automatically. Without that, the agent still has the tool available and will use it when it looks up Razorpay docs. |
| **"I already have GitHub Copilot / Cursor with the full codebase indexed."** | Indexing your codebase tells the agent about your code. It doesn't tell the agent about Razorpay's current API behavior. Those are different knowledge sources. The docs MCP is about what Razorpay does, not what your code does. |
| **"My team uses Python, but this is listed as for any language."** | The MCP server is written in Python, but the tools it exposes are language-agnostic — they return markdown text and URLs. The agent uses that content to write code in whatever language you're working in: Node.js, Go, Java, Ruby, whatever. |
| **"What does this cost to run?"** | Zero ongoing cost. One-time: `pip install -e .` and a 2–5 minute index build that downloads ~540KB of metadata and ~20MB of markdown. After that: local BM25 search, no API calls, no rate limits, no bill. |
| **"Is the data from Razorpay official?"** | Yes. The source is `razorpay.com/docs/llms.txt` — Razorpay's own machine-readable doc index. Every URL is pulled verbatim from that file. Nothing is scraped, constructed, or inferred. |

---

## Install

```bash
# 1. Clone and install
git clone https://github.com/03shraddha/razorpay_docs_mcp.git
cd razorpay_docs_mcp
pip install -e .

# 2. Build the local index (~2–5 minutes, fetches ~2,200 docs)
python -m razorpay_docs_mcp.refresh
```

Expected output:
```
=== Razorpay Docs MCP — Refresh ===

Fetching https://razorpay.com/docs/llms.txt …
  Downloaded 540,935 bytes
  Found 2,207 doc URLs

Fetching 2,207 markdown files (concurrency=20) …
  Fetched: 2,207  |  Failed/skipped: 0

Opening database: data/razorpay_docs.duckdb
Indexing …

=== Done ===
  Docs indexed : 2,207
  Chunks       : 21,818
  Failures     : 0
  DB path      : data/razorpay_docs.duckdb
```

---

## Register with your AI coding agent

All clients use the same JSON config format — only the config file location differs.

After registering, restart the app. The tools `search_razorpay_docs` and `get_razorpay_docs` will appear in the agent's tool list.

---

### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
`%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "razorpay-docs": {
      "command": "python",
      "args": ["-m", "razorpay_docs_mcp.server"],
      "cwd": "/absolute/path/to/razorpay_docs_mcp"
    }
  }
}
```

---

### Claude Code

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "razorpay-docs": {
      "command": "python",
      "args": ["-m", "razorpay_docs_mcp.server"],
      "cwd": "/absolute/path/to/razorpay_docs_mcp"
    }
  }
}
```

---

### Cursor

Global config: `~/.cursor/mcp.json`
Project-level config: `.cursor/mcp.json` in your project root (takes precedence over global)

```json
{
  "mcpServers": {
    "razorpay-docs": {
      "command": "python",
      "args": ["-m", "razorpay_docs_mcp.server"],
      "cwd": "/absolute/path/to/razorpay_docs_mcp"
    }
  }
}
```

---

### Windsurf

`~/.codeium/windsurf/mcp_config.json`

```json
{
  "mcpServers": {
    "razorpay-docs": {
      "command": "python",
      "args": ["-m", "razorpay_docs_mcp.server"],
      "cwd": "/absolute/path/to/razorpay_docs_mcp"
    }
  }
}
```

---

### VS Code with Cline

Cline stores MCP servers in your VS Code `settings.json` under the `"cline.mcpServers"` key.

Open VS Code settings (`Ctrl+Shift+P` → "Open User Settings (JSON)") and add:

```json
{
  "cline.mcpServers": {
    "razorpay-docs": {
      "command": "python",
      "args": ["-m", "razorpay_docs_mcp.server"],
      "cwd": "/absolute/path/to/razorpay_docs_mcp"
    }
  }
}
```

---

### Continue (VS Code / JetBrains)

`~/.continue/config.json`

Add an entry to the `"mcpServers"` array:

```json
{
  "mcpServers": [
    {
      "name": "razorpay-docs",
      "command": "python",
      "args": ["-m", "razorpay_docs_mcp.server"],
      "cwd": "/absolute/path/to/razorpay_docs_mcp"
    }
  ]
}
```

---

## Register with HTTP clients (remote transport)

These clients connect over HTTP/SSE instead of stdio. You must first start the server in HTTP mode:

```bash
python -m razorpay_docs_mcp.server --transport http
```

This starts the MCP server on port 8000. The SSE endpoint is `http://localhost:8000/sse`.

---

### Claude.ai

Claude.ai supports connecting to external MCP servers via its integrations settings.

1. Go to [claude.ai](https://claude.ai) → Settings → Integrations
2. Click "Add custom integration"
3. Paste your MCP server URL: `http://localhost:8000/sse` (for local) or your deployed HTTPS URL

> **Note:** claude.ai requires HTTPS for publicly deployed servers. For local development, the Claude Desktop app (stdio config above) is the simpler option since it does not require running a separate HTTP server.

---

### ChatGPT Desktop

The ChatGPT desktop app (macOS and Windows) supports MCP via local stdio. The ChatGPT web app does not natively support MCP as of April 2026.

macOS: `~/Library/Application Support/OpenAI/ChatGPT/mcp.json`
Windows: `%APPDATA%\OpenAI\ChatGPT\mcp.json`

```json
{
  "mcpServers": {
    "razorpay-docs": {
      "command": "python",
      "args": ["-m", "razorpay_docs_mcp.server"],
      "cwd": "/absolute/path/to/razorpay_docs_mcp"
    }
  }
}
```

---

## Test it yourself — 5 queries

Run these in Claude Desktop / Cursor after registering the MCP. Each result should include a `razorpay.com/docs/...` URL you can click to verify.

- [ ] **Webhook signature:** *"How do I verify a Razorpay webhook signature in Node.js?"*
  → Should return docs with the `validateWebhookSignature` method and a citable URL.

- [ ] **Subscription schema:** *"What fields does the Subscription resource return on creation?"*
  → Should return the `api/subscriptions` doc with the full field list.

- [ ] **UPI AutoPay:** *"How does UPI AutoPay recurring work?"*
  → Should return the UPI recurring payments doc with setup steps.

- [ ] **Error code:** *"What does Razorpay error BAD_REQUEST_ERROR mean?"*
  → Should hit the `errors/` docs with the error description.

- [ ] **Product filter:** Run query #1 again with `product="webhooks"` as a filter.
  → Should narrow results to webhooks-specific docs only.

**What to look for:** The agent cites a `razorpay.com/docs/...` URL in its response. Click it. If it opens the correct Razorpay page, the MCP is working correctly.

---

## How it works under the hood

```
razorpay.com/docs/llms.txt
        │
        │  (2,200+ raw GitHub markdown URLs)
        ▼
   ingest.py  ──►  fetches all docs concurrently (httpx, 20 workers)
        │
        │  splits each doc into chunks at ## headings
        │  tracks "H1 > H2 > H3" breadcrumb per chunk
        ▼
   DuckDB (local file)
        │  docs table  — url, title, product, metadata
        │  chunks table — chunk_id, content, heading_path
        │  BM25 FTS index over chunks
        ▼
   server.py  (FastMCP — stdio or HTTP/SSE)
        │
        ├── search_razorpay_docs(query, product?, limit?)
        │       BM25 search → top N chunks → snippets + URLs
        │
        └── get_razorpay_docs(urls[])
                fetch chunks → reassemble full markdown
```

No embedding API. No vector database. No external service at query time. The entire thing runs locally from a single DuckDB file.

---

## Refresh the index

Run this whenever Razorpay ships a major update, or before starting a new integration:

```bash
python -m razorpay_docs_mcp.refresh
```

It re-downloads everything from Razorpay's official source and rebuilds the index in place. Safe to run at any time — the old data is replaced atomically.

---

## Tools reference

| Tool | Required input | Optional input | Output |
|---|---|---|---|
| `search_razorpay_docs` | `query: str` | `product: str` (payments \| api \| x \| partners \| payroll \| pos \| webhooks \| errors), `limit: int` (default 10, max 25) | `{ results: [{ url, title, heading_path, snippet, product, score }] }` |
| `get_razorpay_docs` | `urls: list[str]` (max 20 canonical razorpay.com/docs/... URLs) | — | `{ documents: [{ url, title, product, content }], not_found: [] }` |

Every response uses canonical `razorpay.com/docs/...` URLs — never raw GitHub URLs. The agent cites these back to you, and you can verify them in one click.
