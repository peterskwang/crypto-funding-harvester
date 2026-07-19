"""Loads per-asset daily bars and aligns them onto a common trading
calendar (crypto trades 24/7, so a union of all dates works -- unlike FX,
there's no weekend gap to reconcile)."""

from __future__ import annotations

import json
from typing import Dict, List

from crypto_trend_strategy import config


def load_daily(symbol: str) -> List[dict]:
    with open(config.DATA_FILES[symbol]) as fp:
        bars = json.load(fp)
    return sorted(bars, key=lambda b: b["date"][:10])


def load_all(start_date: str = None) -> Dict[str, List[dict]]:
    """Returns {symbol: bars}, each filtered to start_date onward (if given)."""
    out = {}
    for symbol in config.SYMBOLS:
        bars = load_daily(symbol)
        if start_date:
            bars = [b for b in bars if b["date"][:10] >= start_date]
        out[symbol] = bars
    return out


def common_calendar(all_bars: Dict[str, List[dict]]) -> List[str]:
    """Union of all trading dates across all assets, sorted -- the master
    calendar the backtest steps through. An asset simply has no bar (and
    is excluded from that day's universe) on dates before it listed."""
    dates = set()
    for bars in all_bars.values():
        dates.update(b["date"][:10] for b in bars)
    return sorted(dates)
