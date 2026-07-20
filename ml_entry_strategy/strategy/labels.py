"""Triple-barrier labeling -- objective ground truth for "was this a good
entry". For each candidate bar, walk FORWARD to see which of three
barriers is hit first:

  - profit target:  entry +/- PROFIT_TARGET_ATR_MULT * ATR
  - stop-loss:       entry -/+ STOP_LOSS_ATR_MULT * ATR
  - time limit:      MAX_HOLD_BARS bars with neither barrier touched

Label = 1 if the profit target is hit before the stop-loss and before the
time limit, else 0. This looks forward from the candidate bar, which is
standard supervised-learning label construction -- not lookahead bias.
Lookahead bias is a FEATURE using future data; features.py never does
that. Labels are the ground truth we're trying to predict; they're
allowed, and expected, to look forward.

Intrabar ambiguity: if a single forward bar's range touches BOTH the
profit and stop barriers, the true order in which price traveled within
that bar is unknown from OHLC alone (no tick data). We resolve it with a
simple, disclosed heuristic: compare the bar's open to each barrier and
assume price reached whichever barrier is closer to the open first. This
is the same kind of disclosed approximation used elsewhere in this
project (volume delta, volume profile) where OHLCV can't fully reconstruct
intrabar path.
"""

from __future__ import annotations

from typing import List, Optional

from ml_entry_strategy import config
from ml_entry_strategy.strategy import features


def _resolve_bar(bar: dict, profit_barrier: float, stop_barrier: float, direction: str) -> Optional[str]:
    """Returns 'profit', 'stop', or None (neither touched) for one forward
    bar, given the barrier levels and trade direction."""
    high, low, open_ = bar["high"], bar["low"], bar["open"]
    if direction == "long":
        hit_profit = high >= profit_barrier
        hit_stop = low <= stop_barrier
    else:
        hit_profit = low <= profit_barrier
        hit_stop = high >= stop_barrier

    if hit_profit and hit_stop:
        dist_to_profit = abs(open_ - profit_barrier)
        dist_to_stop = abs(open_ - stop_barrier)
        return "stop" if dist_to_stop <= dist_to_profit else "profit"
    if hit_profit:
        return "profit"
    if hit_stop:
        return "stop"
    return None


def _label_one(bars: List[dict], t: int, atr: float, direction: str) -> Optional[dict]:
    n = len(bars)
    if t + config.MAX_HOLD_BARS >= n:
        return None  # not enough forward bars to resolve -- excluded, not guessed

    entry_price = bars[t]["close"]
    if direction == "long":
        profit_barrier = entry_price + config.PROFIT_TARGET_ATR_MULT * atr
        stop_barrier = entry_price - config.STOP_LOSS_ATR_MULT * atr
    else:
        profit_barrier = entry_price - config.PROFIT_TARGET_ATR_MULT * atr
        stop_barrier = entry_price + config.STOP_LOSS_ATR_MULT * atr

    for bars_held in range(1, config.MAX_HOLD_BARS + 1):
        outcome = _resolve_bar(bars[t + bars_held], profit_barrier, stop_barrier, direction)
        if outcome == "profit":
            exit_price = profit_barrier
            ret = (exit_price - entry_price) / entry_price if direction == "long" else (entry_price - exit_price) / entry_price
            return {"label": 1, "exit_reason": "profit", "bars_held": bars_held, "realized_return": ret}
        if outcome == "stop":
            exit_price = stop_barrier
            ret = (exit_price - entry_price) / entry_price if direction == "long" else (entry_price - exit_price) / entry_price
            return {"label": 0, "exit_reason": "stop", "bars_held": bars_held, "realized_return": ret}

    exit_price = bars[t + config.MAX_HOLD_BARS]["close"]
    ret = (exit_price - entry_price) / entry_price if direction == "long" else (entry_price - exit_price) / entry_price
    return {"label": 0, "exit_reason": "time", "bars_held": config.MAX_HOLD_BARS, "realized_return": ret}


def label_bars(bars: List[dict], direction: str) -> List[Optional[dict]]:
    """direction: 'long' or 'short'. Returns one entry per bar (None where
    there's not enough forward data to resolve, i.e. the last
    MAX_HOLD_BARS bars of the series, or ATR warm-up hasn't finished)."""
    assert direction in ("long", "short")
    atr_series = features.raw_atr(bars)
    out: List[Optional[dict]] = []
    for t in range(len(bars)):
        atr = atr_series[t]
        if atr is None:
            out.append(None)
            continue
        out.append(_label_one(bars, t, atr, direction))
    return out
