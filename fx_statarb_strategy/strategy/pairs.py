"""Spread construction and regime detection for the EURUSD/GBPUSD pair.

The spread is defined in log-price space (log(EURUSD) - beta * log(GBPUSD))
so that beta is a genuine hedge ratio (dimensionless), not an artifact of
the two pairs having different price scales.
"""

from __future__ import annotations

import math
from typing import List, Optional


def ols_beta(y: List[float], x: List[float]) -> float:
    """Simple OLS slope of y on x (no intercept needed since we only use
    the slope as a hedge ratio): beta = cov(x,y) / var(x)."""
    n = len(y)
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    var = sum((x[i] - mean_x) ** 2 for i in range(n))
    if var == 0:
        return 0.0
    return cov / var


def log_prices(closes: List[float]) -> List[float]:
    return [math.log(c) for c in closes]


def static_hedge_ratio(eurusd_closes: List[float], gbpusd_closes: List[float]) -> float:
    """One beta fit once over the given window (used by v1-v3; v4+ uses a
    rolling beta instead, see rolling_hedge_ratios)."""
    return ols_beta(log_prices(eurusd_closes), log_prices(gbpusd_closes))


def rolling_hedge_ratios(
    eurusd_closes: List[float], gbpusd_closes: List[float], lookback: int,
    update_every: int = 1, ewma_alpha: Optional[float] = None,
) -> List[Optional[float]]:
    """beta[t] estimated from closes[t-lookback:t] (strictly backward-
    looking, no lookahead) -- None for the first `lookback` bars.

    Two real bugs were found and fixed here during v4.0 development, both
    worth keeping visible rather than silently patching:

    1. Re-fitting the OLS regression fresh every single bar (update_every=1,
       ewma_alpha=None) sounds most "responsive" but injects fresh
       estimation noise into the spread every step -- bar-to-bar spread
       volatility roughly quadrupled versus a static beta on this data,
       drowning out the regime filter entirely (0 trades passed it).

    2. The naive fix -- re-fit only every N bars and hold beta fixed
       between updates -- traded that continuous noise for discrete JUMPS:
       measured on this data, the median spread jump exactly at an update
       boundary was ~300x the median jump elsewhere (0.031 vs 0.0001),
       because the spread is redefined the instant beta steps to a new
       value. Every v4.0a trade (37/37) hit its stop-loss, not because the
       relationship broke down, but because of this artifact.

    The actual fix (ewma_alpha set): re-fit the raw OLS beta every bar
    (so it always reflects the freshest lookback window) but only let the
    USED beta move toward it exponentially, smoothed_beta[t] = alpha *
    raw_beta[t] + (1-alpha) * smoothed_beta[t-1]. This is both responsive
    and continuous -- no re-estimation noise spike, no discrete jump."""
    y = log_prices(eurusd_closes)
    x = log_prices(gbpusd_closes)
    n = len(y)
    out: List[Optional[float]] = [None] * n

    if ewma_alpha is not None:
        smoothed = None
        for t in range(lookback, n):
            raw = ols_beta(y[t - lookback:t], x[t - lookback:t])
            smoothed = raw if smoothed is None else ewma_alpha * raw + (1 - ewma_alpha) * smoothed
            out[t] = smoothed
        return out

    last_beta = None
    for t in range(lookback, n):
        if last_beta is None or (t - lookback) % update_every == 0:
            last_beta = ols_beta(y[t - lookback:t], x[t - lookback:t])
        out[t] = last_beta
    return out


def spread_series(eurusd_closes: List[float], gbpusd_closes: List[float], beta) -> List[float]:
    """beta can be a single float (static) or a list of per-bar betas
    (rolling) the same length as the closes."""
    y = log_prices(eurusd_closes)
    x = log_prices(gbpusd_closes)
    if isinstance(beta, list):
        return [y[i] - beta[i] * x[i] if beta[i] is not None else None for i in range(len(y))]
    return [y[i] - beta * x[i] for i in range(len(y))]


def rolling_zscore(series: List[Optional[float]], lookback: int) -> List[Optional[float]]:
    """z[t] = (series[t] - mean(series[t-lookback:t])) / std(series[t-lookback:t]),
    strictly backward-looking. None where there isn't enough valid history
    or the window is degenerate (zero variance)."""
    n = len(series)
    out: List[Optional[float]] = [None] * n
    for t in range(n):
        if series[t] is None:
            continue
        window = [v for v in series[max(0, t - lookback):t] if v is not None]
        if len(window) < lookback // 2:  # require a reasonably full window
            continue
        mean = sum(window) / len(window)
        var = sum((v - mean) ** 2 for v in window) / len(window)
        std = math.sqrt(var)
        if std == 0:
            continue
        out[t] = (series[t] - mean) / std
    return out


def variance_ratio(series: List[float], k: int) -> Optional[float]:
    """Lo-MacKinlay-style variance ratio: Var(k-bar returns) / (k * Var(1-bar
    returns)). VR < 1 indicates mean-reverting (sub-diffusive) behavior over
    that horizon; VR ~= 1 indicates a random walk; VR > 1 indicates
    trending (super-diffusive) behavior. Returns None if there isn't enough
    data or the 1-bar variance is degenerate."""
    n = len(series)
    if n < k * 4:
        return None
    one_bar_returns = [series[i] - series[i - 1] for i in range(1, n)]
    k_bar_returns = [series[i] - series[i - k] for i in range(k, n)]

    def _var(values):
        m = sum(values) / len(values)
        return sum((v - m) ** 2 for v in values) / len(values)

    var_1 = _var(one_bar_returns)
    if var_1 == 0:
        return None
    var_k = _var(k_bar_returns)
    return var_k / (k * var_1)
