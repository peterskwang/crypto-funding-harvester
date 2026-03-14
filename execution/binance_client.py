"""Minimal Binance Futures public data client."""
from __future__ import annotations

from typing import Dict, List, Optional

import requests

BASE_URL = "https://fapi.binance.com"
TIMEOUT = 10


class BinanceFuturesClient:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{BASE_URL}{path}"
        response = self.session.get(url, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()

    def get_funding_rates(self, symbols: List[str]) -> Dict[str, float]:
        """Fetches the current funding rate for a list of symbols."""
        rates: Dict[str, float] = {}
        for symbol in symbols:
            data = self._get("/fapi/v1/premiumIndex", params={"symbol": symbol})
            last_rate = data.get("lastFundingRate")
            if last_rate is None:
                continue
            rates[symbol] = float(last_rate)
        return rates

    def get_funding_rate_history(self, symbol: str, limit: int = 10) -> List[dict]:
        """Fetches historical funding rates for a symbol."""
        data = self._get(
            "/fapi/v1/fundingRate",
            params={"symbol": symbol, "limit": limit},
        )
        if not isinstance(data, list):
            return []
        return data

    def get_latest_price(self, symbol: str) -> float:
        """Fetches the latest mark price for a symbol."""
        data = self._get("/fapi/v1/premiumIndex", params={"symbol": symbol})
        mark_price = data.get("markPrice")
        if mark_price is None:
            raise ValueError(f"No mark price returned for {symbol}")
        return float(mark_price)
