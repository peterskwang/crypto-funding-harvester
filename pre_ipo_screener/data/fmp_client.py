"""Minimal Financial Modeling Prep client for IPO calendar, ticker, and daily
bar data. Drop-in alternative to PolygonClient: returns records already
mapped into the same field names universe.py / historical.py / backtest.py
expect (ticker, issuer_name, listing_date, primary_exchange, min/max_offer_price,
total_offer_size for IPO records; "o"/"c"/"date" for bars) so no other module
needs to know which data source is in use.

Endpoint paths follow FMP's "stable" API as of this writing
(https://financialmodelingprep.com/stable/...) -- verify against current FMP
docs once network access is available, the same way PolygonClient's field
names should be spot-checked against a live response before trusting it.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import requests

BASE_URL = "https://financialmodelingprep.com/stable"
TIMEOUT = 15
API_KEY_ENV_VAR = "FMP_API_KEY"


class FMPAuthError(RuntimeError):
    """Raised when FMP_API_KEY is missing or rejected."""


def _parse_price_range(price_range: Optional[str]) -> "tuple[Optional[float], Optional[float]]":
    if not price_range:
        return None, None
    parts = re.split(r"\s*-\s*", price_range.strip())
    try:
        if len(parts) == 2:
            return float(parts[0]), float(parts[1])
        if len(parts) == 1:
            value = float(parts[0])
            return value, value
    except ValueError:
        pass
    return None, None


def _ipo_record_to_polygon_shape(record: Dict[str, Any]) -> Dict[str, Any]:
    min_price, max_price = _parse_price_range(record.get("priceRange"))
    return {
        "ticker": record.get("symbol"),
        "issuer_name": record.get("company"),
        "listing_date": record.get("date"),
        "primary_exchange": record.get("exchange"),
        "min_offer_price": min_price,
        "max_offer_price": max_price,
        "shares_outstanding": record.get("shares"),
        "total_offer_size": record.get("marketCap"),
    }


def _bar_to_polygon_shape(bar: Dict[str, Any]) -> Dict[str, Any]:
    return {"date": bar.get("date"), "o": bar.get("open"), "c": bar.get("close")}


class FMPClient:
    def __init__(self, api_key: Optional[str] = None, session: Optional[requests.Session] = None):
        self.api_key = api_key or os.environ.get(API_KEY_ENV_VAR)
        self.session = session or requests.Session()

    def _get(self, path: str, params: Optional[dict] = None) -> Any:
        if not self.api_key:
            raise FMPAuthError(
                f"{API_KEY_ENV_VAR} is not set. Configure it in the environment before running live scans."
            )
        url = f"{BASE_URL}/{path}"
        query = dict(params or {})
        query["apikey"] = self.api_key
        response = self.session.get(url, params=query, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()

    def get_ipos(
        self,
        listing_date_gte: Optional[str] = None,
        listing_date_lte: Optional[str] = None,
        ipo_status: Optional[str] = None,  # unused; FMP's ipos-calendar doesn't filter by status
        limit: int = 250,
    ) -> List[dict]:
        """Fetches IPO calendar records, normalized into the same shape
        PolygonClient.get_ipos returns so normalize_ipo_record() works unchanged.
        """
        params: Dict[str, str] = {"limit": str(limit)}
        if listing_date_gte:
            params["from"] = listing_date_gte
        if listing_date_lte:
            params["to"] = listing_date_lte

        data = self._get("ipos-calendar", params=params)
        return [_ipo_record_to_polygon_shape(record) for record in (data or [])]

    def get_daily_bars(self, ticker: str, from_date: str, to_date: str) -> List[dict]:
        """Fetches daily OHLC bars for a ticker, ascending (oldest first) --
        FMP returns them descending, so this reverses before returning.
        """
        data = self._get(
            "historical-price-eod/full",
            params={"symbol": ticker, "from": from_date, "to": to_date},
        )
        bars = [_bar_to_polygon_shape(bar) for bar in (data or [])]
        return list(reversed(bars))

    def get_ticker_details(self, ticker: str) -> dict:
        """Fetches company profile metadata (sector, market cap, description)."""
        data = self._get("profile", params={"symbol": ticker})
        if not data:
            return {}
        profile = data[0]
        return {
            "sic_description": profile.get("sector"),
            "sector": profile.get("sector"),
            "market_cap": profile.get("marketCap"),
        }
