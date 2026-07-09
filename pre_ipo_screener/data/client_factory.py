"""Picks a live data client based on whichever API key is configured in the
environment. Both clients expose the same interface (get_ipos, get_daily_bars,
get_ticker_details) with fields already normalized to the same shape, so the
rest of the screener never needs to know which one is in use.
"""
from __future__ import annotations

import os

from pre_ipo_screener.data.fmp_client import FMPClient
from pre_ipo_screener.data.polygon_client import PolygonClient


class NoDataSourceConfigured(RuntimeError):
    """Raised when neither POLYGON_API_KEY nor FMP_API_KEY is set."""


def get_client():
    """Prefers Polygon if POLYGON_API_KEY is set, otherwise falls back to FMP
    if FMP_API_KEY is set. Raises if neither is configured.
    """
    if os.environ.get("POLYGON_API_KEY"):
        return PolygonClient()
    if os.environ.get("FMP_API_KEY"):
        return FMPClient()
    raise NoDataSourceConfigured(
        "Set POLYGON_API_KEY or FMP_API_KEY in the environment before running live scans."
    )
