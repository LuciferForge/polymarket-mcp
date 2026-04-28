"""Polymarket MCP — Model Context Protocol server exposing Polymarket prediction market data.

Wraps api.protodex.io (the LuciferForge Polymarket data API) as MCP tools so AI agents
(Claude Desktop, Cursor, Cline, Continue, etc.) can natively query live prediction markets.
"""

__version__ = "0.1.0"
__author__ = "LuciferForge"
__license__ = "MIT"

from .client import PolymarketClient

__all__ = ["PolymarketClient", "__version__"]
