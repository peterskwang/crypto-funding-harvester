"""Minimal Polygon.io client for IPO calendar, ticker, and aggregate bar data."""
from __future__ import annotations

import os
from typing import Dict, List, Optional

import requests

BASE_URL = "https://api.polygon.io"
TIMEOUT = 15
API_KEY_ENV_VAR = "POLYGON_API_KEY"


class PolygonAuthError(RuntimeError):
    """Raised when POLYGON_API_KEY is missing or rejected."""


class PolygonClient:
    def __init__(self, api_key: Optional[str] = None, session: Optional[requests.Session] = None):
        self.api_key = api_key or os.environ.get(API_KEY_ENV_VAR)
        self.session = session or requests.Session()

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        if not self.api_key:
            raise PolygonAuthError(
                f"{API_KEY_ENV_VAR} is not set. Configure it in the environment before running live scans."
            )
        url = f"{BASE_URL}{path}"
        query = dict(params or {})
        query["apiKey"] = self.api_key
        response = self.session.get(url, params=query, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()

    def get_ipos(
        self,
        listing_date_gte: Optional[str] = None,
        listing_date_lte: Optional[str] = None,
        ipo_status: Optional[str] = None,
        limit: int = 250,
    ) -> List[dict]:
        """Fetches IPO records from Polygon's IPOs reference endpoint.

        `listing_date_*` are ISO date strings (YYYY-MM-DD). `ipo_status` is
        one of Polygon's statuses, e.g. "new", "history", "postponed", "withdrawn".
        """
        params: Dict[str, str] = {"limit": str(limit), "sort": "listing_date", "order": "asc"}
        if listing_date_gte:
            params["listing_date.gte"] = listing_date_gte
        if listing_date_lte:
            params["listing_date.lte"] = listing_date_lte
        if ipo_status:
            params["ipo_status"] = ipo_status

        results: List[dict] = []
        path = "/vX/reference/ipos"
        while path:
            data = self._get(path, params=params)
            results.extend(data.get("results", []))
            next_url = data.get("next_url")
            if not next_url:
                break
            # next_url is a fully-qualified URL already carrying its own params/cursor.
            path = next_url.replace(BASE_URL, "")
            params = {}
        return results

    def get_daily_bars(self, ticker: str, from_date: str, to_date: str) -> List[dict]:
        """Fetches daily OHLCV bars for a ticker between two ISO dates (inclusive)."""
        path = f"/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}"
        data = self._get(path, params={"adjusted": "true", "sort": "asc", "limit": 5000})
        results = data.get("results") or []
        return results

    def get_ticker_details(self, ticker: str) -> dict:
        """Fetches reference metadata (sector, market cap, description) for a ticker."""
        data = self._get(f"/v3/reference/tickers/{ticker}")
        return data.get("results") or {}
