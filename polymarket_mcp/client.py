"""Thin HTTP client for api.protodex.io (the LuciferForge Polymarket Data API).

Default base URL: https://api.protodex.io
Free tier: 100 requests/day, no key required.
Pro tier: 10K requests/day with POLYMARKET_API_KEY env var.

This is the abstraction boundary — all Polymarket data goes through our API,
not direct CLOB queries (except orderbook depth, which isn't yet on our API).
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx


DEFAULT_BASE_URL = os.environ.get("POLYMARKET_API_BASE", "https://api.protodex.io")
DEFAULT_TIMEOUT = float(os.environ.get("POLYMARKET_API_TIMEOUT", "20.0"))


class PolymarketAPIError(RuntimeError):
    """Raised when the upstream API returns a non-2xx response."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"api.protodex.io error {status}: {detail}")
        self.status = status
        self.detail = detail


class PolymarketClient:
    """Synchronous HTTP client for the Polymarket Data API.

    MCP tool calls are request/response, so a sync client keeps tool code simple.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("POLYMARKET_API_KEY")
        self.timeout = timeout
        headers = {
            "User-Agent": "polymarket-mcp/0.1.0 (+https://github.com/LuciferForge/polymarket-mcp)",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "PolymarketClient":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal: GET wrapper with error handling
    # ------------------------------------------------------------------
    def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        # Filter out None values so optional query params don't become "None"
        clean_params = (
            {k: v for k, v in params.items() if v is not None} if params else None
        )
        try:
            resp = self._client.get(path, params=clean_params)
        except httpx.HTTPError as e:
            raise PolymarketAPIError(0, f"network error: {e}") from e

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise PolymarketAPIError(resp.status_code, str(detail))

        try:
            return resp.json()
        except Exception as e:
            raise PolymarketAPIError(resp.status_code, f"invalid JSON: {e}") from e

    # ------------------------------------------------------------------
    # Public endpoints (mirrors api.protodex.io)
    # ------------------------------------------------------------------
    def stats(self) -> dict:
        return self._get("/stats")

    def categories(self) -> list[dict]:
        return self._get("/categories")

    def list_markets(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort: str = "volume",
        limit: int = 20,
        offset: int = 0,
        active: bool = True,
    ) -> dict:
        return self._get(
            "/markets",
            {
                "category": category,
                "search": search,
                "sort": sort,
                "limit": limit,
                "offset": offset,
                "active": str(active).lower(),
            },
        )

    def get_market(self, market_id: str) -> dict:
        return self._get(f"/markets/{market_id}")

    def get_prices(
        self,
        market_id: str,
        outcome: str = "Yes",
        limit: int = 100,
        since: Optional[str] = None,
    ) -> dict:
        return self._get(
            f"/markets/{market_id}/prices",
            {"outcome": outcome, "limit": limit, "since": since},
        )

    def get_crashes(
        self,
        threshold: float = 0.15,
        hours: int = 4,
        category: Optional[str] = None,
    ) -> dict:
        return self._get(
            "/crashes",
            {"threshold": threshold, "hours": hours, "category": category},
        )


# ---------------------------------------------------------------------
# Polymarket CLOB (orderbook) — direct call, since not on our API yet.
# Documented as v0.2 territory; kept here so the MCP tool can opportunistically
# call it without forcing a heavy py-clob-client dependency.
# ---------------------------------------------------------------------

POLYMARKET_CLOB_BASE = os.environ.get("POLYMARKET_CLOB_BASE", "https://clob.polymarket.com")


def fetch_orderbook(token_id: str, timeout: float = 10.0) -> dict:
    """Fetch the current orderbook for a Polymarket CLOB token id.

    Calls clob.polymarket.com directly. No auth needed for read-only book queries.
    Returns the raw response: {market, asset_id, bids: [...], asks: [...], hash, timestamp}.
    """
    url = f"{POLYMARKET_CLOB_BASE}/book"
    headers = {
        "User-Agent": "polymarket-mcp/0.1.0 (+https://github.com/LuciferForge/polymarket-mcp)",
        "Accept": "application/json",
    }
    try:
        resp = httpx.get(url, params={"token_id": token_id}, headers=headers, timeout=timeout)
    except httpx.HTTPError as e:
        raise PolymarketAPIError(0, f"clob network error: {e}") from e

    if resp.status_code >= 400:
        raise PolymarketAPIError(resp.status_code, resp.text)
    return resp.json()
