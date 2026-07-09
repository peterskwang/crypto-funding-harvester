"""Backtests the screener's scoring methodology against realized IPO price history.

Replays the exact scoring rules used for live runs (scoring.score_upcoming /
score_fade_candidates) against historical candidates, then simulates the
resulting trade's entry/exit price and holding period per its suggested
style, and reports the realized return. This only produces a trustworthy
report when fed real daily bars — see run_backtest.py.

Look-ahead bias: candidates are processed in listing-date order, and the
analog-group table used to score each candidate is built only from IPOs that
listed strictly before it, matching what a live weekly run would have known
at the time.

Known simplification: the lockup-expiry short signal is evaluated using
however much real trading history a candidate has accumulated by the time
the backtest runs, not by replaying a daily job day-by-day through the whole
window. A candidate is only included in that bucket if its bars actually
reach the lockup entry offset (see run_backtest's incomplete-history guard).
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from pre_ipo_screener import config
from pre_ipo_screener.screener import historical, scoring


def _bar_close_at(bars: List[dict], index: int) -> Optional[float]:
    if not bars:
        return None
    index = min(index, len(bars) - 1)
    return bars[index].get("c")


def _bar_date_at(bars: List[dict], index: int) -> Optional[str]:
    if not bars:
        return None
    index = min(index, len(bars) - 1)
    bar = bars[index]
    return bar.get("date") or bar.get("t")


def _style_exit_day(style: str) -> int:
    if "Day 1-2" in style:
        return config.INTRADAY_EXIT_DAY
    if "swing" in style:
        return config.SWING_EXIT_DAY
    return config.POSITION_EXIT_DAY


def simulate_long_trade(candidate: Dict[str, Any], bars: List[dict], style: str) -> Optional[Dict[str, Any]]:
    if not bars:
        return None
    entry_price = _bar_close_at(bars, 0)
    exit_index = _style_exit_day(style)
    exit_price = _bar_close_at(bars, exit_index)
    if not entry_price or not exit_price:
        return None

    return {
        "ticker": candidate["ticker"],
        "name": candidate.get("name", ""),
        "direction": "LONG",
        "style": style,
        "entry_date": _bar_date_at(bars, 0),
        "entry_price": round(entry_price, 2),
        "exit_date": _bar_date_at(bars, exit_index),
        "exit_price": round(exit_price, 2),
        "holding_days": min(exit_index, len(bars) - 1),
        "return_pct": (exit_price - entry_price) / entry_price,
    }


def simulate_momentum_fade_trade(candidate: Dict[str, Any], bars: List[dict]) -> Optional[Dict[str, Any]]:
    closes = [b.get("c") for b in bars if b.get("c") is not None]
    if not closes:
        return None
    peak_index = closes.index(max(closes))
    exit_index = min(peak_index + config.MOMENTUM_FADE_HOLD_DAYS, len(bars) - 1)
    entry_price = closes[peak_index]
    exit_price = _bar_close_at(bars, exit_index)
    if not entry_price or not exit_price or exit_index <= peak_index:
        return None

    return {
        "ticker": candidate["ticker"],
        "name": candidate.get("name", ""),
        "direction": "SHORT",
        "style": "Momentum fade",
        "entry_date": _bar_date_at(bars, peak_index),
        "entry_price": round(entry_price, 2),
        "exit_date": _bar_date_at(bars, exit_index),
        "exit_price": round(exit_price, 2),
        "holding_days": exit_index - peak_index,
        "return_pct": (entry_price - exit_price) / entry_price,  # profit if price falls
    }


def simulate_lockup_short_trade(candidate: Dict[str, Any], bars: List[dict]) -> Optional[Dict[str, Any]]:
    entry_index = config.LOCKUP_WINDOW_DAYS[0]
    if len(bars) - 1 < entry_index:
        return None  # not enough trading history to have reached the lockup window

    exit_index = min(entry_index + config.LOCKUP_SHORT_HOLD_DAYS, len(bars) - 1)
    entry_price = _bar_close_at(bars, entry_index)
    exit_price = _bar_close_at(bars, exit_index)
    if not entry_price or not exit_price:
        return None

    return {
        "ticker": candidate["ticker"],
        "name": candidate.get("name", ""),
        "direction": "SHORT",
        "style": "Lockup-expiry short",
        "entry_date": _bar_date_at(bars, entry_index),
        "entry_price": round(entry_price, 2),
        "exit_date": _bar_date_at(bars, exit_index),
        "exit_price": round(exit_price, 2),
        "holding_days": exit_index - entry_index,
        "return_pct": (entry_price - exit_price) / entry_price,
    }


def run_backtest(candidates_with_bars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """candidates_with_bars: each dict must have the normalized candidate fields
    (ticker, name, listing_date, total_offer_size, sector_tag) plus performance
    fields from historical.compute_post_ipo_performance (day1_pop,
    decay_from_high, realized_volatility) and a raw "bars" list.
    """
    ordered = sorted(candidates_with_bars, key=lambda c: c["listing_date"])
    analog_pool: List[Dict[str, Any]] = []
    trades: List[Dict[str, Any]] = []

    for candidate in ordered:
        bars = candidate.get("bars") or []
        listing_date = dt.date.fromisoformat(candidate["listing_date"])

        # Only ever look at IPOs that priced strictly before this one -- no lookahead.
        analog_groups = historical.build_analog_groups(analog_pool, client=None) if analog_pool else {}

        scored = scoring.score_upcoming(candidate, analog_groups, today=listing_date)
        if scored["direction"] == "LONG":
            style = scoring.suggested_style({"reasons": [], "realized_volatility": candidate.get("realized_volatility")})
            trade = simulate_long_trade(candidate, bars, style)
            if trade:
                trades.append(trade)

        day1_pop = candidate.get("day1_pop")
        decay_from_high = candidate.get("decay_from_high")
        if (
            day1_pop is not None
            and day1_pop >= config.FADE_DAY1_POP_THRESHOLD
            and decay_from_high is not None
            and decay_from_high <= config.FADE_DECAY_THRESHOLD
        ):
            trade = simulate_momentum_fade_trade(candidate, bars)
            if trade:
                trades.append(trade)

        lockup_trade = simulate_lockup_short_trade(candidate, bars)
        if lockup_trade:
            trades.append(lockup_trade)

        analog_pool.append(candidate)

    return trades


def summarize_trades(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not trades:
        return {"count": 0}

    def _bucket_stats(subset: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not subset:
            return {"count": 0, "win_rate": None, "avg_return": None}
        returns = [t["return_pct"] for t in subset]
        wins = [r for r in returns if r > 0]
        return {
            "count": len(subset),
            "win_rate": len(wins) / len(subset),
            "avg_return": sum(returns) / len(subset),
        }

    longs = [t for t in trades if t["direction"] == "LONG"]
    shorts = [t for t in trades if t["direction"] == "SHORT"]
    best = max(trades, key=lambda t: t["return_pct"])
    worst = min(trades, key=lambda t: t["return_pct"])

    return {
        "count": len(trades),
        "overall": _bucket_stats(trades),
        "long": _bucket_stats(longs),
        "short": _bucket_stats(shorts),
        "best_trade": best,
        "worst_trade": worst,
    }
