"""Smoke tests for polymarket_mcp.

These tests verify the module imports cleanly, all expected tools are registered,
and the CLI's --list-tools and --help paths work without network access.
"""

from __future__ import annotations

import subprocess
import sys


EXPECTED_TOOLS = {
    "get_stats",
    "list_markets",
    "get_market",
    "get_prices",
    "get_crashes",
    "get_categories",
    "get_orderbook",
}


def test_module_imports() -> None:
    import polymarket_mcp
    import polymarket_mcp.server  # noqa: F401
    import polymarket_mcp.client  # noqa: F401

    assert polymarket_mcp.__version__ == "0.1.0"


def test_all_tools_registered() -> None:
    from polymarket_mcp.server import list_registered_tools

    tools = set(list_registered_tools())
    missing = EXPECTED_TOOLS - tools
    assert not missing, f"Missing tools: {missing}"


def test_tools_have_docstrings() -> None:
    """MCP uses the docstring as the tool description shown to the agent."""
    from polymarket_mcp import server

    for name in EXPECTED_TOOLS:
        fn = getattr(server, name, None)
        assert fn is not None, f"Tool {name} not exported from server module"
        # FastMCP wraps the function; the original is preserved on __wrapped__
        # in most decorator implementations. Accept either path.
        target = getattr(fn, "__wrapped__", fn)
        doc = (target.__doc__ or "").strip()
        assert doc, f"Tool {name} is missing a docstring"
        assert len(doc) > 30, f"Tool {name} docstring is too short to be useful"


def test_cli_list_tools() -> None:
    """python -m polymarket_mcp.server --list-tools must exit 0 and print tool names."""
    result = subprocess.run(
        [sys.executable, "-m", "polymarket_mcp.server", "--list-tools"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, f"--list-tools exited {result.returncode}: {result.stderr}"
    printed = set(line.strip() for line in result.stdout.splitlines() if line.strip())
    missing = EXPECTED_TOOLS - printed
    assert not missing, f"--list-tools missing: {missing}"


def test_cli_help() -> None:
    """python -m polymarket_mcp.server --help must exit 0."""
    result = subprocess.run(
        [sys.executable, "-m", "polymarket_mcp.server", "--help"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0
    assert "polymarket-mcp" in result.stdout.lower()


def test_client_constructs_without_network() -> None:
    """Constructing the client must not fire any HTTP requests."""
    from polymarket_mcp.client import PolymarketClient

    c = PolymarketClient()
    try:
        assert c.base_url.startswith("http")
    finally:
        c.close()
