# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.1] - 2026-04-28

### Changed
- Tightened version constraints on dependencies to avoid pip resolver hangs:
  - `fastmcp>=2.0.0,<3.0.0` (was unbounded)
  - `httpx>=0.27.0,<1.0.0` (was unbounded)

### Notes
- No code changes. Same 7 MCP tools, same behavior. v0.1.0 still works if you already have it installed; the dep ranges are just stricter to make first-time `pip install` faster on Python 3.10 with old pip.

## [0.1.0] - 2026-04-28

### Added
- Initial public release.
- 7 MCP tools: `get_stats`, `list_markets`, `get_market`, `get_prices`, `get_crashes`, `get_categories`, `get_orderbook`.
- FastMCP-based server, supports stdio (Claude Desktop, Cursor, Cline) and HTTP transports.
- Backed by `api.protodex.io` data layer indexing 9,500+ Polymarket markets.
- 6/6 unit tests passing.
- MIT license.

### Note
- PyPI distribution name is `polymarket-mcp-pro` because the bare `polymarket-mcp` name was already taken on PyPI by an unrelated package. The Python module, CLI command, and GitHub repo all stay `polymarket_mcp` / `polymarket-mcp`.

[0.1.1]: https://github.com/LuciferForge/polymarket-mcp/releases/tag/v0.1.1
[0.1.0]: https://github.com/LuciferForge/polymarket-mcp/releases/tag/v0.1.0
