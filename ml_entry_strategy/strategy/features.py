"""Feature engineering -- every feature here is computed strictly from
bars up to and including the current bar (and in most cases strictly
BEFORE the current bar, to avoid even same-bar look-ahead where noted).
This is the boundary that must never be crossed: label construction
(labels.py) is allowed to look forward, features here are never allowed
to."""

from __future__ import annotations

import math
from typing import List, Optional

from ml_entry_strategy import config


def true_range(bars: List[dict]) -> List[Optional[float]]:
    out: List[Optional[float]] = [None]
    for i in range(1, len(bars)):
        h, l, prev_c = bars[i]["high"], bars[i]["low"], bars[i - 1]["close"]
        out.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    return out


def raw_atr(bars: List[dict], lookback: int = None) -> List[Optional[float]]:
    """ATR in price units (not normalized) -- used to size triple-barrier
    levels in labels.py. atr_pct() below is the normalized version used as
    a model feature; this is the same underlying calc, kept separate so
    the barrier construction isn't tangled up with feature scaling."""
    lookback = lookback or config.ATR_LOOKBACK
    tr = true_range(bars)
    n = len(bars)
    out: List[Optional[float]] = [None] * n
    for t in range(n):
        window = [v for v in tr[max(0, t - lookback + 1):t + 1] if v is not None]
        if len(window) < lookback:
            continue
        out[t] = sum(window) / len(window)
    return out


def atr_pct(bars: List[dict], lookback: int = None) -> List[Optional[float]]:
    """ATR / close, so it's comparable across different price levels."""
    atr = raw_atr(bars, lookback)
    return [a / bars[t]["close"] if a is not None and bars[t]["close"] else None
            for t, a in enumerate(atr)]


def volume_zscore(bars: List[dict], lookback: int = None) -> List[Optional[float]]:
    """Today's volume compared to the PRIOR `lookback` bars' mean/std
    (today's own volume excluded from the baseline, so this measures
    'how unusual is this bar's volume vs recent history', not a
    self-referential average)."""
    lookback = lookback or config.VOLUME_ZSCORE_LOOKBACK
    n = len(bars)
    out: List[Optional[float]] = [None] * n
    for t in range(lookback, n):
        window = [bars[i]["volume"] for i in range(t - lookback, t)]
        mean = sum(window) / len(window)
        var = sum((v - mean) ** 2 for v in window) / len(window)
        std = math.sqrt(var)
        if std == 0:
            continue
        out[t] = (bars[t]["volume"] - mean) / std
    return out


def volume_delta_norm(bars: List[dict]) -> List[Optional[float]]:
    """Chaikin-style close-location buy/sell split, normalized to
    [-1, 1] by dividing by the bar's own volume -- an approximation of
    order-flow imbalance, not real tick-level order flow (forex/crypto
    OHLCV has no true aggressor data; same disclosed limitation as the
    eurusd_strategy and fx_statarb_strategy projects earlier this
    session)."""
    out: List[Optional[float]] = []
    for b in bars:
        high, low, close, volume = b["high"], b["low"], b["close"], b["volume"]
        rng = high - low
        if rng <= 0 or volume <= 0:
            out.append(0.0)
            continue
        buy_volume = volume * (close - low) / rng
        sell_volume = volume * (high - close) / rng
        out.append((buy_volume - sell_volume) / volume)
    return out


def price_acceleration(bars: List[dict], k: int = None) -> List[Optional[float]]:
    """Change in k-bar rate-of-change between two consecutive k-bar
    windows -- a discrete second derivative of price."""
    k = k or config.PRICE_ACCEL_LOOKBACK
    n = len(bars)
    out: List[Optional[float]] = [None] * n
    for t in range(2 * k, n):
        c0, ck, c2k = bars[t]["close"], bars[t - k]["close"], bars[t - 2 * k]["close"]
        if not ck or not c2k:
            continue
        roc_recent = (c0 - ck) / ck
        roc_prior = (ck - c2k) / c2k
        out[t] = roc_recent - roc_prior
    return out


def surge_ratio(bars: List[dict], lookback: int = None) -> List[Optional[float]]:
    """This bar's high-low range vs the mean range of the PRIOR
    `lookback` bars (today's own range excluded from the baseline)."""
    lookback = lookback or config.SURGE_LOOKBACK
    n = len(bars)
    out: List[Optional[float]] = [None] * n
    for t in range(lookback, n):
        window = [bars[i]["high"] - bars[i]["low"] for i in range(t - lookback, t)]
        mean_range = sum(window) / len(window)
        if mean_range == 0:
            continue
        today_range = bars[t]["high"] - bars[t]["low"]
        out[t] = today_range / mean_range
    return out


def dist_from_poc_pct(bars: List[dict], lookback: int = None, n_bins: int = None) -> List[Optional[float]]:
    """Approximate volume profile over the PRIOR `lookback` bars (today
    excluded): bin each of those bars' typical price (H+L+C)/3 into
    `n_bins` bins spanning that window's price range, accumulate volume
    per bin, find the point of control (POC, the bin with the most
    volume), and return how far today's close is from the POC price, as
    a percentage. This is an approximation (real volume profile needs
    intra-bar/tick data to know exactly where within each bar's range
    volume traded); disclosed as such."""
    lookback = lookback or config.VOLUME_PROFILE_LOOKBACK
    n_bins = n_bins or config.VOLUME_PROFILE_BINS
    n = len(bars)
    out: List[Optional[float]] = [None] * n
    for t in range(lookback, n):
        window = bars[t - lookback:t]
        typical_prices = [(b["high"] + b["low"] + b["close"]) / 3 for b in window]
        lo, hi = min(typical_prices), max(typical_prices)
        if hi <= lo:
            continue
        bin_width = (hi - lo) / n_bins
        bin_volume = [0.0] * n_bins
        for b, tp in zip(window, typical_prices):
            idx = min(int((tp - lo) / bin_width), n_bins - 1)
            bin_volume[idx] += b["volume"]
        poc_idx = max(range(n_bins), key=lambda i: bin_volume[i])
        poc_price = lo + (poc_idx + 0.5) * bin_width
        if poc_price == 0:
            continue
        out[t] = (bars[t]["close"] - poc_price) / poc_price
    return out


def compute_all_features(bars: List[dict]) -> dict:
    return {
        "atr_pct": atr_pct(bars),
        "volume_zscore": volume_zscore(bars),
        "volume_delta_norm": volume_delta_norm(bars),
        "price_accel": price_acceleration(bars),
        "surge_ratio": surge_ratio(bars),
        "dist_from_poc_pct": dist_from_poc_pct(bars),
    }
