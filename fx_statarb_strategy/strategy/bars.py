"""Loads raw 5-min bars, aggregates to 15-min, and aligns two symbols onto
a common timestamp index (inner join -- only keep bars where both symbols
have data, since a pairs trade needs both legs)."""

from __future__ import annotations

import json
from typing import Dict, List

from fx_statarb_strategy import config


def load_5m(symbol: str) -> List[dict]:
    with open(config.DATA_FILES[symbol]) as fp:
        bars = json.load(fp)
    return sorted(bars, key=lambda b: b["date"])


def aggregate_15m(bars_5m: List[dict]) -> List[dict]:
    """Groups consecutive 5-min bars into 15-min bars by wall-clock bucket
    (floor the minute to the nearest 15). Bars are only combined if they're
    contiguous within the same bucket -- a gap (e.g. weekend) just starts a
    fresh bucket, it doesn't get bridged."""
    buckets: Dict[str, List[dict]] = {}
    order: List[str] = []
    for bar in bars_5m:
        date_part, time_part = bar["date"].split(" ")
        hh, mm, ss = time_part.split(":")
        bucket_minute = (int(mm) // config.SIGNAL_TIMEFRAME_MINUTES) * config.SIGNAL_TIMEFRAME_MINUTES
        bucket_key = f"{date_part} {hh}:{bucket_minute:02d}:00"
        if bucket_key not in buckets:
            buckets[bucket_key] = []
            order.append(bucket_key)
        buckets[bucket_key].append(bar)

    out = []
    for key in order:
        group = buckets[key]
        out.append({
            "date": key,
            "open": group[0]["open"],
            "high": max(b["high"] for b in group),
            "low": min(b["low"] for b in group),
            "close": group[-1]["close"],
            "volume": sum(b.get("volume", 0) for b in group),
            "n_5m_bars": len(group),
        })
    return out


def align(bars_a: List[dict], bars_b: List[dict]) -> "tuple[List[dict], List[dict]]":
    """Inner-joins two bar series on the 'date' key, returning both series
    filtered to only the timestamps present in both (same length, same
    order)."""
    dates_a = {b["date"]: b for b in bars_a}
    dates_b = {b["date"]: b for b in bars_b}
    common = sorted(set(dates_a) & set(dates_b))
    return [dates_a[d] for d in common], [dates_b[d] for d in common]


def load_aligned_15m(symbol_a: str, symbol_b: str) -> "tuple[List[dict], List[dict]]":
    a_5m = load_5m(symbol_a)
    b_5m = load_5m(symbol_b)
    a_15m = aggregate_15m(a_5m)
    b_15m = aggregate_15m(b_5m)
    return align(a_15m, b_15m)
