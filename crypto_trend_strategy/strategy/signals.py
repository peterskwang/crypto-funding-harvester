"""Time-series momentum signal and volatility-targeted position sizing,
per-asset. Strictly backward-looking at every step -- no lookahead."""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from crypto_trend_strategy import config


def daily_returns(closes: List[float]) -> List[Optional[float]]:
    out: List[Optional[float]] = [None]
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        out.append((closes[i] - prev) / prev if prev else None)
    return out


def realized_vol(returns: List[Optional[float]], lookback: int) -> List[Optional[float]]:
    """Trailing daily-return stdev over `lookback` days, using only
    returns[t-lookback:t] (excludes today's return, since today's return
    isn't known yet when sizing today's trade)."""
    n = len(returns)
    out: List[Optional[float]] = [None] * n
    for t in range(n):
        window = [r for r in returns[max(0, t - lookback):t] if r is not None]
        if len(window) < lookback // 2:
            continue
        mean = sum(window) / len(window)
        var = sum((r - mean) ** 2 for r in window) / len(window)
        out[t] = math.sqrt(var)
    return out


def momentum_composite(closes: List[float], vol: List[Optional[float]], lookbacks: List[int] = None) -> List[Optional[float]]:
    """composite[t] = mean over each lookback L of the L-day return,
    risk-adjusted by the trailing daily vol scaled to that horizon
    (sqrt(L)) -- a simple Sharpe-like normalization so a 30-day and a
    200-day lookback contribute on a comparable scale rather than the
    longer window mechanically dominating. Requires closes[t-max(lookbacks)]
    to exist and vol[t] to be already computed (also backward-looking)."""
    lookbacks = lookbacks or config.MOMENTUM_LOOKBACKS_DAYS
    n = len(closes)
    out: List[Optional[float]] = [None] * n
    max_lb = max(lookbacks)
    for t in range(max_lb, n):
        if vol[t] is None or vol[t] == 0:
            continue
        scores = []
        for lb in lookbacks:
            past = closes[t - lb]
            if not past:
                continue
            raw_return = (closes[t] - past) / past
            risk_adj = raw_return / (vol[t] * math.sqrt(lb))
            scores.append(risk_adj)
        if scores:
            out[t] = sum(scores) / len(scores)
    return out


def compute_asset_signals(bars: List[dict]) -> Dict[str, list]:
    closes = [b["close"] for b in bars]
    rets = daily_returns(closes)
    vol = realized_vol(rets, config.VOL_LOOKBACK_DAYS)
    momentum = momentum_composite(closes, vol, config.MOMENTUM_LOOKBACKS_DAYS)

    direction: List[Optional[int]] = [None] * len(closes)
    raw_weight: List[Optional[float]] = [None] * len(closes)
    for t in range(len(closes)):
        if momentum[t] is None or vol[t] is None or vol[t] == 0:
            continue
        direction[t] = 1 if momentum[t] > config.MOMENTUM_ENTRY_THRESHOLD else (
            -1 if momentum[t] < -config.MOMENTUM_ENTRY_THRESHOLD else 0
        )
        if direction[t] == 0:
            raw_weight[t] = 0.0
            continue
        annualized_vol = vol[t] * math.sqrt(365)
        vol_target_weight = config.TARGET_ANNUALIZED_VOL_PER_ASSET / annualized_vol if annualized_vol else 0.0
        capped = min(vol_target_weight, config.MAX_ASSET_WEIGHT)
        raw_weight[t] = direction[t] * capped

    return {
        "closes": closes,
        "returns": rets,
        "vol": vol,
        "momentum": momentum,
        "direction": direction,
        "raw_weight": raw_weight,
    }
