# polymarket-mcp

[![PyPI](https://img.shields.io/pypi/v/polymarket-mcp-pro.svg)](https://pypi.org/project/polymarket-mcp-pro/)
[![Python](https://img.shields.io/pypi/pyversions/polymarket-mcp-pro.svg)](https://pypi.org/project/polymarket-mcp-pro/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Live Polymarket prediction-market data, exposed as MCP tools for Claude / Cursor / Cline.**

A [Model Context Protocol](https://modelcontextprotocol.io) server that lets any MCP-compatible AI agent query live Polymarket markets natively — list markets by volume, pull historical price snapshots, find recent crashes (mean-reversion candidates), and inspect order-book depth, all without writing custom HTTP code in your prompts.

Backed by [`api.protodex.io`](https://api.protodex.io) — the LuciferForge Polymarket data layer indexing **9,500+ markets** with a price snapshot every 15 minutes.

> Why this exists: Polymarket has a public API but no MCP-native interface. Generic LLM tools can search the web for stale wiki entries; this gives your agent **live, structured prediction-market data** with crash signals it can reason over directly.

---

## What's in the box

Seven tools, all read-only, all returning structured JSON the agent can consume:

| Tool | What it does |
| --- | --- |
| `get_stats` | Dataset-wide counts and freshness timestamps |
| `list_markets` | Paginated market list with category, search, sort filters |
| `get_market` | Single market detail with outcomes and CLOB token ids |
| `get_prices` | Historical price snapshots for a Yes/No outcome |
| `get_crashes` | Markets that dropped >= N% in the last H hours (default 15% / 4h) |
| `get_categories` | Category breakdown with market counts and volume |
| `get_orderbook` | Live bid/ask depth for a CLOB token id |

Coming in v0.2: WebSocket crash subscription bridged into the MCP transport.

---

## Install

### Zero-install (recommended)

If you have [`uv`](https://docs.astral.sh/uv/) (every modern MCP client setup does):

```bash
uvx --from polymarket-mcp-pro polymarket-mcp
```

Then point your client at `uvx --from polymarket-mcp-pro polymarket-mcp`. Done — no virtualenv to manage, always pulls the latest version.

### pip

```bash
pip install polymarket-mcp-pro
polymarket-mcp --help
```

> Note: PyPI distribution name is `polymarket-mcp-pro` (the bare `polymarket-mcp` name was already taken by an unrelated package). The CLI command and Python module both stay `polymarket_mcp`.

### From source

```bash
git clone https://github.com/LuciferForge/polymarket-mcp.git
cd polymarket-mcp
pip install -e .
polymarket-mcp --list-tools
```

---

## Configure your client

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows) and add:

```json
{
  "mcpServers": {
    "polymarket": {
      "command": "uvx",
      "args": ["polymarket-mcp"],
      "env": {
        "POLYMARKET_API_KEY": ""
      }
    }
  }
}
```

Restart Claude Desktop. The `polymarket` tools will appear in the tool picker.

A drop-in copy of this snippet lives at [`examples/claude_desktop_config.json`](./examples/claude_desktop_config.json).

### Cursor

In Cursor settings -> Features -> MCP Servers, add:

```json
{
  "mcpServers": {
    "polymarket": {
      "command": "uvx",
      "args": ["polymarket-mcp"],
      "env": {
        "POLYMARKET_API_KEY": ""
      }
    }
  }
}
```

A drop-in copy lives at [`examples/cursor_config.json`](./examples/cursor_config.json).

### Cline / Continue / other MCP clients

Any client that speaks MCP stdio transport works. Use the same command (`uvx --from polymarket-mcp-pro polymarket-mcp`) and env block.

---

## Usage examples

These are sample prompts you can paste into the AI agent. The agent will pick the right tool automatically — these are illustrative, not the literal API surface.

### Find recent prediction-market crashes

> "Use polymarket get_crashes to show me politics markets that dropped at least 20% in the last 6 hours, ordered by largest drop."

The agent calls `get_crashes(threshold=0.20, hours=6, category="politics")` and gets back a list of markets with current price, recent high, and percent drop.

### Pull a price history for analysis

> "List the top 5 crypto markets by 24-hour volume on Polymarket, then fetch the last 200 price snapshots for the highest-volume one."

The agent chains `list_markets(category="crypto", sort="volume_24h", limit=5)` -> `get_prices(market_id, outcome="Yes", limit=200)` and can plot, summarize, or feed the series into another tool.

### Inspect order-book depth before sizing a trade idea

> "Get the Polymarket market for `0x1234...` and show me the live orderbook for the Yes outcome."

The agent calls `get_market(market_id)`, reads the `outcomes_detail[].clob_token_id` for the Yes outcome, then calls `get_orderbook(token_id)` to inspect the live book.

---

## Pricing tiers

`api.protodex.io` is free for light usage and paid for production volume.

| Tier | Limit | How to get it |
| --- | --- | --- |
| Free | 100 requests/day | No key required. Just install. |
| Sample | 1-day full dataset | $1 one-time -- [Gumroad](https://manja8.gumroad.com/l/polymarket-data) |
| Standard | 10,000 requests/day, 30 days | $9 one-time -- [Gumroad](https://manja8.gumroad.com/l/agyjd) |
| Cross-signal | 30,000 requests/day, 30 days | $29 one-time -- [Gumroad](https://manja8.gumroad.com/l/cross-signal-dataset) |

After purchase, email `LuciferForge@proton.me` with your Gumroad purchase id and you'll receive an API key. Set it via the `POLYMARKET_API_KEY` env var in your MCP client config.

Storefront: <https://manja8.gumroad.com>.

Self-serve key issuance is on the roadmap.

---

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `POLYMARKET_API_KEY` | _(unset)_ | Pro tier key. Without it you get the free 100/day tier. |
| `POLYMARKET_API_BASE` | `https://api.protodex.io` | Override the API base (e.g. for self-hosting). |
| `POLYMARKET_API_TIMEOUT` | `20` | HTTP timeout in seconds. |

---

## Related projects in the LuciferForge stack

- [`api.protodex.io`](https://api.protodex.io) -- the underlying free API this server wraps.
- [LuciferForge/polymarket-historical-data](https://github.com/LuciferForge/polymarket-historical-data) -- the historical Polymarket dataset (CSV / Parquet).
- [LuciferForge/polymarket-crash-bot](https://github.com/LuciferForge/polymarket-crash-bot) -- the live mean-reversion trading bot built on top of the same data.

These three sit on the same data layer, so anything you can query through this MCP server is exactly what the bot trades on.

---

## Development

```bash
git clone https://github.com/LuciferForge/polymarket-mcp.git
cd polymarket-mcp
pip install -e ".[dev]"
pytest -q
polymarket-mcp --list-tools
```

Run the server in HTTP transport mode for manual testing:

```bash
polymarket-mcp --transport http --port 8765
```

---

## License

MIT. See [`LICENSE`](./LICENSE).

## Author

[LuciferForge](https://github.com/LuciferForge) -- builds the Polymarket data layer at [api.protodex.io](https://api.protodex.io) and runs [protodex.io](https://protodex.io), the largest MCP server directory (5,800+ servers indexed).
