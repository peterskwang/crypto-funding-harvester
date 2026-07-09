"""Post-IPO performance calculation and sector x deal-size analog grouping."""
from __future__ import annotations

import datetime as dt
import statistics
from typing import Any, Dict, List, Optional

from pre_ipo_screener import config
from pre_ipo_screener.data.polygon_client import PolygonClient

SECTOR_KEYWORD_FALLBACK = {
    "AI": ["ARTIFICIAL INTELLIGENCE", " AI ", "AI,"],
    "BIOTECH": ["PHARMA", "BIOTECH", "THERAPEUTIC", "MEDICINE", "BIOSCIENCE"],
    "FINTECH": ["FINTECH", "FINANCIAL", "CAPITAL", "BANK"],
    "CRYPTO": ["CRYPTO", "BITCOIN", "BLOCKCHAIN", "DIGITAL ASSET"],
    "ENERGY": ["ENERGY", "NUCLEAR", "SOLAR", "MINING", "MINERALS", "METALS"],
    "SPACE": ["SPACE", "AEROSPACE"],
    "TECH": ["TECH", "SOFTWARE", "CLOUD", "DATA", "QUANTUM", "SEMICONDUCTOR"],
    "HEALTH": ["HEALTH", "MEDICAL", "DIAGNOSTIC"],
}


def get_sector_tag(client: PolygonClient, candidate: Dict[str, Any]) -> str:
    try:
        details = client.get_ticker_details(candidate["ticker"])
    except Exception:
        details = {}
    sector = details.get("sic_description") or details.get("sector")
    if sector:
        return str(sector).upper()

    name = candidate.get("name", "").upper()
    for tag, keywords in SECTOR_KEYWORD_FALLBACK.items():
        if any(keyword in name for keyword in keywords):
            return tag
    return "OTHER"


def deal_size_tier(total_offer_size: Optional[float]) -> str:
    if total_offer_size is None:
        return "unknown"
    for tier, (low, high) in config.DEAL_SIZE_TIERS.items():
        if low <= total_offer_size < high:
            return tier
    return "unknown"


def _pct_change(new: float, old: float) -> Optional[float]:
    if old in (0, None):
        return None
    return (new - old) / old


def compute_post_ipo_performance(client: PolygonClient, candidate: Dict[str, Any], today: Optional[dt.date] = None) -> Dict[str, Any]:
    """Pulls daily bars since listing and annotates the candidate with performance metrics."""
    today = today or dt.date.today()
    listing_date = candidate["listing_date"]
    result = dict(candidate)

    try:
        bars = client.get_daily_bars(candidate["ticker"], listing_date, today.isoformat())
    except Exception:
        bars = []

    if not bars:
        result.update(
            {
                "day1_pop": None,
                "week1_return": None,
                "month1_return": None,
                "realized_volatility": None,
                "current_price": None,
                "decay_from_high": None,
                "trading_days_elapsed": 0,
                "bars": [],
            }
        )
        return result

    closes = [bar["c"] for bar in bars if "c" in bar]
    opens = [bar["o"] for bar in bars if "o" in bar]

    day1_pop = _pct_change(closes[0], opens[0]) if closes and opens else None
    week1_idx = min(config.WEEK1_WINDOW, len(closes) - 1)
    month1_idx = min(config.MONTH1_WINDOW, len(closes) - 1)
    week1_return = _pct_change(closes[week1_idx], closes[0]) if closes else None
    month1_return = _pct_change(closes[month1_idx], closes[0]) if closes else None

    daily_returns = [
        _pct_change(closes[i], closes[i - 1]) for i in range(1, len(closes))
        if closes[i - 1]
    ]
    daily_returns = [r for r in daily_returns if r is not None]
    realized_volatility = statistics.pstdev(daily_returns) if len(daily_returns) >= 2 else None

    max_close = max(closes) if closes else None
    current_price = closes[-1] if closes else None
    decay_from_high = _pct_change(current_price, max_close) if max_close else None

    result.update(
        {
            "day1_pop": day1_pop,
            "week1_return": week1_return,
            "month1_return": month1_return,
            "realized_volatility": realized_volatility,
            "current_price": current_price,
            "decay_from_high": decay_from_high,
            "trading_days_elapsed": len(closes),
            "bars": bars,
        }
    )
    return result


def build_analog_groups(recent_candidates_with_perf: List[Dict[str, Any]], client: PolygonClient) -> Dict[str, Dict[str, Any]]:
    """Groups recent IPOs by sector x deal-size tier and averages their returns.

    Returns a dict keyed by "SECTOR|tier" -> {avg_week1_return, avg_month1_return, count, tickers}.
    """
    groups: Dict[str, Dict[str, Any]] = {}
    for candidate in recent_candidates_with_perf:
        if candidate.get("week1_return") is None:
            continue
        sector = candidate.get("sector_tag") or get_sector_tag(client, candidate)
        tier = deal_size_tier(candidate.get("total_offer_size"))
        key = f"{sector}|{tier}"
        groups.setdefault(key, {"sector": sector, "tier": tier, "week1_returns": [], "month1_returns": [], "tickers": []})
        groups[key]["week1_returns"].append(candidate["week1_return"])
        if candidate.get("month1_return") is not None:
            groups[key]["month1_returns"].append(candidate["month1_return"])
        groups[key]["tickers"].append(candidate["ticker"])

    summary: Dict[str, Dict[str, Any]] = {}
    for key, data in groups.items():
        summary[key] = {
            "sector": data["sector"],
            "tier": data["tier"],
            "count": len(data["week1_returns"]),
            "avg_week1_return": statistics.mean(data["week1_returns"]),
            "avg_month1_return": statistics.mean(data["month1_returns"]) if data["month1_returns"] else None,
            "tickers": data["tickers"],
        }
    return summary
