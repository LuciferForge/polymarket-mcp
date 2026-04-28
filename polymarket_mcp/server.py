"""Polymarket MCP server — FastMCP entrypoint.

Exposes Polymarket prediction-market data as MCP tools for Claude Desktop, Cursor,
Cline, Continue, and any other MCP-compatible AI agent.

Run:
    python -m polymarket_mcp.server
or, after install:
    polymarket-mcp

Configuration (environment variables):
    POLYMARKET_API_KEY      Optional. Pro tier key (10K req/day). Free tier (100/day) without.
    POLYMARKET_API_BASE     Override API base URL. Default: https://api.protodex.io
    POLYMARKET_API_TIMEOUT  HTTP timeout in seconds. Default: 20.

All Polymarket data flows through api.protodex.io (the LuciferForge data layer).
The single exception is `get_orderbook`, which calls clob.polymarket.com directly
because live order-book depth is not yet exposed via the API. This will move to
api.protodex.io in v0.2.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Optional

from fastmcp import FastMCP

from .client import PolymarketAPIError, PolymarketClient, fetch_orderbook


# ---------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------
mcp: FastMCP = FastMCP(
    name="polymarket-mcp",
    instructions=(
        "Live Polymarket prediction-market data. Use these tools to look up markets, "
        "fetch historical prices, find recent crashes (mean-reversion candidates), and "
        "inspect order-book depth. All read-only; no trading. Backed by api.protodex.io."
    ),
)


def _get_client() -> PolymarketClient:
    """Build a fresh client per call. Cheap (no connection pool reuse needed at MCP scale)."""
    return PolymarketClient()


def _format_error(e: PolymarketAPIError) -> dict:
    """Convert API errors into a structured dict the agent can reason about."""
    return {
        "error": True,
        "status": e.status,
        "detail": e.detail,
        "hint": (
            "If status=429, you hit the free tier (100/day). Set POLYMARKET_API_KEY env var "
            "with a paid key from https://manja8.gumroad.com (the $9 30-day plan = 10K/day)."
        ) if e.status == 429 else None,
    }


# ---------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------

@mcp.tool()
def get_stats() -> dict:
    """Get dataset-wide statistics for the Polymarket data API.

    Returns counts of markets, price snapshots, and order-book snapshots,
    plus the earliest and latest data timestamps and the update cadence.
    Use this to confirm freshness before relying on price data.
    """
    try:
        with _get_client() as c:
            return c.stats()
    except PolymarketAPIError as e:
        return _format_error(e)


@mcp.tool()
def list_markets(
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = "volume",
    limit: int = 20,
    offset: int = 0,
    active: bool = True,
) -> dict:
    """List Polymarket prediction markets, paginated and filterable.

    Args:
        category: Filter to a single category (e.g. "politics", "sports", "crypto",
            "economics"). Use get_categories() to discover valid values.
        search: Substring match against the market question text.
        sort: Sort order. One of "volume", "volume_24h", "name". Default "volume".
        limit: How many markets to return (1-200). Default 20.
        offset: Pagination offset. Default 0.
        active: Only return currently-tradeable markets. Default True.

    Returns:
        Dict with `total`, `limit`, `offset`, and `markets`: a list of dicts each
        containing id, question, category, volume, volume_24h, liquidity, end_date,
        best_bid, best_ask, spread, last_trade_price, one_day_change, active.
    """
    try:
        with _get_client() as c:
            return c.list_markets(
                category=category,
                search=search,
                sort=sort,
                limit=limit,
                offset=offset,
                active=active,
            )
    except PolymarketAPIError as e:
        return _format_error(e)


@mcp.tool()
def get_market(market_id: str) -> dict:
    """Fetch full detail for a single Polymarket market, including outcomes.

    Args:
        market_id: The Polymarket market id (a numeric string from list_markets()).

    Returns:
        Full market record plus `outcomes_detail`: a list of outcomes with their
        clob_token_id values (used by get_orderbook() for live book depth).
    """
    try:
        with _get_client() as c:
            return c.get_market(market_id)
    except PolymarketAPIError as e:
        return _format_error(e)


@mcp.tool()
def get_prices(
    market_id: str,
    outcome: str = "Yes",
    limit: int = 100,
    since: Optional[str] = None,
) -> dict:
    """Get historical price snapshots for a market outcome.

    Args:
        market_id: The Polymarket market id.
        outcome: Either "Yes" or "No". Default "Yes".
        limit: Max snapshots to return (1-5000). Default 100, ordered newest-first.
        since: Optional ISO-8601 timestamp. Only return snapshots strictly after this.

    Returns:
        Dict with `market_id`, `outcome`, `count`, and `prices`:
        a list of {price, ts} entries sorted newest-first.
    """
    try:
        with _get_client() as c:
            return c.get_prices(market_id, outcome=outcome, limit=limit, since=since)
    except PolymarketAPIError as e:
        return _format_error(e)


@mcp.tool()
def get_crashes(
    threshold: float = 0.15,
    hours: int = 4,
    category: Optional[str] = None,
) -> dict:
    """Find Polymarket markets that have dropped at least N% in the last H hours.

    These are mean-reversion candidates. The underlying API notes that historically,
    after a >20% crash the average bounce is +6.6% within 15 minutes (across 5,629
    measured events).

    Args:
        threshold: Minimum drop fraction (0.05 to 0.50). 0.15 = 15% drop. Default 0.15.
        hours: Lookback window in hours (1-24). Default 4.
        category: Optional category filter (e.g. "politics", "sports").

    Returns:
        Dict with `threshold`, `hours`, `count`, `note`, and `crashes`: a list of
        {market_id, high, current, drop_pct, question, category, volume} entries
        sorted by largest drop first, capped at 50.
    """
    try:
        with _get_client() as c:
            return c.get_crashes(threshold=threshold, hours=hours, category=category)
    except PolymarketAPIError as e:
        return _format_error(e)


@mcp.tool()
def get_categories() -> list[dict]:
    """Get the list of Polymarket categories with market counts and volume.

    Returns:
        List of {category, count, volume_millions} sorted by market count (descending).
        Use the `category` value from this list as the filter input to list_markets()
        and get_crashes().
    """
    try:
        with _get_client() as c:
            return c.categories()
    except PolymarketAPIError as e:
        # Tools can return either dict or list; for consistency, wrap errors in a list.
        return [_format_error(e)]


@mcp.tool()
def get_orderbook(token_id: str) -> dict:
    """Get the current order-book bid/ask depth for a Polymarket CLOB token.

    Calls clob.polymarket.com directly (not via api.protodex.io). The token_id is
    the `clob_token_id` field from `get_market(...).outcomes_detail`.

    Args:
        token_id: The CLOB token id (per outcome, not per market).

    Returns:
        {market, asset_id, bids: [{price, size}, ...], asks: [{price, size}, ...],
         hash, timestamp}. Bids are sorted descending by price; asks ascending.
        On error, returns {error, status, detail}.

    Notes:
        - This is the only tool that bypasses api.protodex.io. Will move there in v0.2.
        - Read-only; no auth needed for book snapshots.
    """
    try:
        return fetch_orderbook(token_id)
    except PolymarketAPIError as e:
        return _format_error(e)


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="polymarket-mcp",
        description=(
            "Polymarket MCP server — exposes live prediction-market data as Model "
            "Context Protocol tools for Claude Desktop, Cursor, Cline, and other "
            "MCP-compatible agents."
        ),
        epilog=(
            "Environment:\n"
            "  POLYMARKET_API_KEY      Pro tier key (optional)\n"
            "  POLYMARKET_API_BASE     Override API base URL (default: https://api.protodex.io)\n"
            "  POLYMARKET_API_TIMEOUT  HTTP timeout seconds (default: 20)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "http", "sse"),
        default=os.environ.get("POLYMARKET_MCP_TRANSPORT", "stdio"),
        help="MCP transport. Default 'stdio' (used by Claude Desktop, Cursor, Cline).",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("POLYMARKET_MCP_HOST", "127.0.0.1"),
        help="Bind host for http/sse transports. Default 127.0.0.1.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("POLYMARKET_MCP_PORT", "8765")),
        help="Bind port for http/sse transports. Default 8765.",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="Print the registered tool names and exit (does not start the server).",
    )
    return parser


def list_registered_tools() -> list[str]:
    """Return the names of all tools registered on the MCP instance.

    Used by tests and the --list-tools CLI flag.
    """
    # FastMCP exposes tools in different ways across versions. Try the
    # public API first, fall back to private attrs only if needed.
    tm = getattr(mcp, "_tool_manager", None) or getattr(mcp, "tool_manager", None)
    if tm is not None:
        tools = getattr(tm, "_tools", None) or getattr(tm, "tools", None) or {}
        if isinstance(tools, dict):
            return sorted(tools.keys())
        if isinstance(tools, list):
            return sorted(getattr(t, "name", str(t)) for t in tools)
    # Last resort: introspect module-level decorated functions.
    return sorted([
        "get_stats",
        "list_markets",
        "get_market",
        "get_prices",
        "get_crashes",
        "get_categories",
        "get_orderbook",
    ])


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    if args.list_tools:
        for name in list_registered_tools():
            print(name)
        return 0

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        print(f"Unknown transport: {args.transport}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
