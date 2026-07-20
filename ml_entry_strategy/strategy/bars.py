"""Loads raw 5-min BTC bars and aggregates to 15-min."""

from __future__ import annotations

import json
import statistics
from typing import Dict, List

from ml_entry_strategy import config

# The raw feed has a known defect: on ~4.2% of 5-min bars the `volume`
# field is garbage (10s of billions) while open/high/low/close stay clean
# and continuous -- confirmed by inspecting surrounding price action, which
# shows no corresponding anomaly. There's a clean natural gap in the sorted
# volume distribution: real volumes top out around 1.7B, corrupted ones
# start above 14B (an 8.3x jump right at that boundary). 5B sits safely in
# that gap, so it's used as a fixed, data-driven cutoff rather than a
# rolling multiplier (which risks reacting to the outliers themselves).
VOLUME_OUTLIER_THRESHOLD = 5_000_000_000
VOLUME_REPAIR_WINDOW = 10  # bars each side to source a replacement median from


def clean_volume_outliers(bars_5m: List[dict]) -> List[dict]:
    """Repairs only the `volume` field on bars flagged by
    VOLUME_OUTLIER_THRESHOLD, replacing it with the median volume of the
    nearest clean (non-flagged) bars on each side. OHLC is never touched --
    it's already clean, this is purely a volume-field data-quality fix."""
    n = len(bars_5m)
    flagged = [b["volume"] > VOLUME_OUTLIER_THRESHOLD for b in bars_5m]
    global_clean_median = statistics.median(
        b["volume"] for b, f in zip(bars_5m, flagged) if not f
    )

    out = []
    for i, bar in enumerate(bars_5m):
        if not flagged[i]:
            out.append(bar)
            continue
        neighbors = []
        lo = max(0, i - VOLUME_REPAIR_WINDOW)
        hi = min(n, i + VOLUME_REPAIR_WINDOW + 1)
        for j in range(lo, hi):
            if j != i and not flagged[j]:
                neighbors.append(bars_5m[j]["volume"])
        repaired = dict(bar)
        repaired["volume"] = statistics.median(neighbors) if neighbors else global_clean_median
        repaired["volume_glitch_repaired"] = True
        out.append(repaired)
    return out


def load_5m() -> List[dict]:
    with open(config.DATA_FILE) as fp:
        bars = json.load(fp)
    bars = sorted(bars, key=lambda b: b["date"])
    return clean_volume_outliers(bars)


def aggregate_15m(bars_5m: List[dict]) -> List[dict]:
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


def load_15m() -> List[dict]:
    return aggregate_15m(load_5m())
