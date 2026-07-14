"""Single-instrument backtest engine for the EURUSD velocity/acceleration
strategy. Reuses the trailing-stop exit design from
pre_ipo_screener/screener/backtest.py._trailing_stop_exit_index, adapted to
a single continuous price series with one position open at a time.

No-lookahead discipline: a strongUp/strongDown signal at bar t is only
computable from bars[0..t] (velocity/acceleration/EMA are all causal). The
trade enters at bar t+1's open, not bar t's close, so the simulated entry
price is one a live system could actually have gotten after the signal bar
closed and confirmed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from eurusd_strategy import config
from eurusd_strategy.strategy import indicators


def generate_signals(bars: List[dict], use_ema_filter: bool, use_delta_filter: bool) -> Dict[str, List]:
    va = indicators.compute_velocity_acceleration(bars)
    ema_trend = indicators.ema_trend_filter(bars)
    delta = indicators.volume_delta_proxy(bars)
    closes = [b["close"] for b in bars]

    long_entry = [False] * len(bars)
    short_entry = [False] * len(bars)
    for t in range(len(bars)):
        up = va["strong_up"][t]
        down = va["strong_down"][t]
        if use_ema_filter:
            up = up and closes[t] > ema_trend[t]
            down = down and closes[t] < ema_trend[t]
        if use_delta_filter:
            up = up and delta[t] > 0
            down = down and delta[t] < 0
        long_entry[t] = up
        short_entry[t] = down

    return {
        **va,
        "ema_trend": ema_trend,
        "delta": delta,
        "long_entry": long_entry,
        "short_entry": short_entry,
    }


def run_backtest(
    bars: List[dict],
    use_ema_filter: bool = True,
    use_delta_filter: bool = True,
    trailing_stop_pct: Optional[float] = None,
    max_hold_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Walks the bar series once, one position at a time (no pyramiding,
    no overlapping trades). A signal that fires while already in a trade
    is ignored -- it is not a live system's job to re-enter mid-trade."""
    trailing_stop_pct = trailing_stop_pct if trailing_stop_pct is not None else config.TRAILING_STOP_PCT
    max_hold_days = max_hold_days if max_hold_days is not None else config.MAX_HOLD_DAYS

    signals = generate_signals(bars, use_ema_filter, use_delta_filter)
    closes = [b["close"] for b in bars]
    dates = [b["date"] for b in bars]
    n = len(bars)

    trades: List[Dict[str, Any]] = []
    t = 0
    while t < n - 1:  # need at least one bar after the signal to enter
        is_long = signals["long_entry"][t]
        is_short = signals["short_entry"][t]
        if not (is_long or is_short):
            t += 1
            continue

        entry_index = t + 1  # enter at next bar's open, not the signal bar's close
        entry_price = bars[entry_index]["open"]
        max_index = min(entry_index + max_hold_days, n - 1)

        exit_index = _trailing_stop_exit_index(
            closes, entry_index, max_index, is_long, trailing_stop_pct
        )
        exit_price = closes[exit_index]

        return_pct = (
            (exit_price - entry_price) / entry_price
            if is_long
            else (entry_price - exit_price) / entry_price
        )

        trades.append({
            "direction": "LONG" if is_long else "SHORT",
            "signal_date": dates[t],
            "entry_date": dates[entry_index],
            "entry_price": round(entry_price, 5),
            "exit_date": dates[exit_index],
            "exit_price": round(exit_price, 5),
            "holding_days": exit_index - entry_index,
            "return_pct": return_pct,
        })

        t = exit_index + 1  # no overlapping trades

    return trades


def _trailing_stop_exit_index(closes, start_index, max_index, is_long, pct):
    max_index = min(max_index, len(closes) - 1)
    extreme = closes[start_index]
    for i in range(start_index + 1, max_index + 1):
        price = closes[i]
        if is_long:
            extreme = max(extreme, price)
            if price <= extreme * (1 - pct):
                return i
        else:
            extreme = min(extreme, price)
            if price >= extreme * (1 + pct):
                return i
    return max_index


def summarize_trades(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not trades:
        return {"count": 0}

    def _bucket_stats(subset):
        if not subset:
            return {"count": 0, "win_rate": None, "avg_return": None}
        returns = [t["return_pct"] for t in subset]
        wins = [r for r in returns if r > 0]
        return {
            "count": len(subset),
            "win_rate": len(wins) / len(subset),
            "avg_return": sum(returns) / len(subset),
            "total_return": sum(returns),
        }

    longs = [t for t in trades if t["direction"] == "LONG"]
    shorts = [t for t in trades if t["direction"] == "SHORT"]
    equity = config.INITIAL_CAPITAL
    peak = equity
    max_drawdown = 0.0
    for t in trades:
        equity *= (1 + t["return_pct"])
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak
        max_drawdown = max(max_drawdown, drawdown)

    best = max(trades, key=lambda t: t["return_pct"])
    worst = min(trades, key=lambda t: t["return_pct"])

    return {
        "count": len(trades),
        "overall": _bucket_stats(trades),
        "long": _bucket_stats(longs),
        "short": _bucket_stats(shorts),
        "final_equity": equity,
        "max_drawdown": max_drawdown,
        "best_trade": best,
        "worst_trade": worst,
    }
