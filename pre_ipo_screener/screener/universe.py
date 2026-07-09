"""Builds the upcoming and recent IPO candidate universes from Polygon data."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from pre_ipo_screener import config
from pre_ipo_screener.data.polygon_client import PolygonClient


def _first_present(record: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    for key in keys:
        if record.get(key) not in (None, ""):
            return record[key]
    return None


def _is_noise(name: str, ticker: str, security_type: Optional[str]) -> bool:
    upper_name = (name or "").upper()
    if any(keyword in upper_name for keyword in config.EXCLUDE_NAME_KEYWORDS):
        return True
    if security_type and security_type.upper() not in ("CS", "ADRC", "ADR"):
        return True
    for suffix in config.EXCLUDE_TICKER_SUFFIXES:
        if ticker.endswith(suffix) and len(ticker) > 1:
            # Only treat as a suffix match if the base ticker also looks like
            # a real listing (avoids dropping short legitimate tickers).
            base = ticker[: -len(suffix)]
            if len(base) >= 2:
                return True
    return False


def normalize_ipo_record(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalizes a raw Polygon IPO record into the screener's candidate shape.

    Returns None if the record is noise (ETF/SPAC shell/trust/etc.) or missing
    the minimum required fields (ticker, name, listing date).
    """
    ticker = _first_present(record, ["ticker"])
    name = _first_present(record, ["issuer_name", "name"])
    listing_date = _first_present(record, ["listing_date", "list_date"])
    if not ticker or not name or not listing_date:
        return None

    security_type = _first_present(record, ["security_type"])
    if _is_noise(str(name), str(ticker), security_type):
        return None

    price_low = _first_present(record, ["min_offer_price", "lowest_offer_price"])
    price_high = _first_present(record, ["max_offer_price", "highest_offer_price"])
    final_price = _first_present(record, ["final_issue_price"])
    shares = _first_present(record, ["shares_outstanding", "total_shares_outstanding", "shares_offered"])
    total_offer_size = _first_present(record, ["total_offer_size"])

    if total_offer_size is None and shares and (final_price or price_high):
        reference_price = final_price or price_high
        try:
            total_offer_size = float(shares) * float(reference_price)
        except (TypeError, ValueError):
            total_offer_size = None

    return {
        "ticker": str(ticker),
        "name": str(name),
        "listing_date": str(listing_date),
        "exchange": _first_present(record, ["primary_exchange", "exchange"]),
        "ipo_status": _first_present(record, ["ipo_status"]),
        "price_low": _to_float(price_low),
        "price_high": _to_float(price_high),
        "final_price": _to_float(final_price),
        "total_offer_size": _to_float(total_offer_size),
    }


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fetch_and_normalize(client: PolygonClient, listing_date_gte: str, listing_date_lte: str) -> List[Dict[str, Any]]:
    raw_records = client.get_ipos(listing_date_gte=listing_date_gte, listing_date_lte=listing_date_lte)
    candidates = []
    for record in raw_records:
        normalized = normalize_ipo_record(record)
        if normalized:
            candidates.append(normalized)
    return candidates


def build_upcoming_universe(client: PolygonClient, today: Optional[dt.date] = None) -> List[Dict[str, Any]]:
    """Fetches operating-company IPOs listing in the next LOOKAHEAD_DAYS."""
    today = today or dt.date.today()
    horizon = today + dt.timedelta(days=config.LOOKAHEAD_DAYS)
    return _fetch_and_normalize(client, today.isoformat(), horizon.isoformat())


def build_recent_universe(client: PolygonClient, today: Optional[dt.date] = None) -> List[Dict[str, Any]]:
    """Fetches operating-company IPOs that listed in the past LOOKBACK_DAYS — the historical reference pool."""
    today = today or dt.date.today()
    start = today - dt.timedelta(days=config.LOOKBACK_DAYS)
    return _fetch_and_normalize(client, start.isoformat(), today.isoformat())
