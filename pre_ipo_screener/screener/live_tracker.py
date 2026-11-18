"""Forward-looking performance tracker for live screener signals.

Every time a run flags a new LONG candidate or a new SHORT (momentum_fade /
lockup_expiry_watch) candidate, this opens a tracked position at that day's
price. On every later run it re-checks each open position's full bar history
and closes it the same way backtest.py would have: a trailing stop of
config.TRAILING_STOP_PCT, capped by the per-signal holding window
(MOMENTUM_FADE_HOLD_DAYS / LOCKUP_SHORT_HOLD_DAYS / POSITION_EXIT_DAY). This
reuses backtest.py's exit logic directly so live results stay comparable to
the backtest rather than using a second, divergent set of rules.

One ticker can only have one open position per signal_type at a time -- a
ticker re-flagged on a later day while already open under the same signal
type is not re-entered.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pre_ipo_screener import config
from pre_ipo_screener.screener.backtest import _trailing_stop_exit_index

_HOLD_DAYS_BY_SIGNAL = {
    "long_watch": config.POSITION_EXIT_DAY,
    "momentum_fade": config.MOMENTUM_FADE_HOLD_DAYS,
    "lockup_expiry_watch": config.LOCKUP_SHORT_HOLD_DAYS,
}


def load_tracker(filepath: Optional[str] = None) -> Dict[str, Any]:
    filepath = filepath or config.TRACKER_FILE_PATH
    path = Path(filepath)
    if not path.exists():
        return {"positions": []}
    with path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    data.setdefault("positions", [])
    return data


def save_tracker(tracker: Dict[str, Any], filepath: Optional[str] = None) -> None:
    filepath = filepath or config.TRACKER_FILE_PATH
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(tracker, fp, indent=2, sort_keys=False)


def _open_keys(tracker: Dict[str, Any]) -> set:
    return {(p["ticker"], p["signal_type"]) for p in tracker["positions"] if p["status"] == "open"}


def _new_position(
    ticker: str,
    name: str,
    direction: str,
    signal_type: str,
    style: str,
    flagged_date: str,
    entry_price: Optional[float],
) -> Dict[str, Any]:
    return {
        "ticker": ticker,
        "name": name,
        "direction": direction,
        "signal_type": signal_type,
        "style": style,
        "flagged_date": flagged_date,
        "entry_price": entry_price,
        "status": "open",
        "current_price": entry_price,
        "unrealized_return_pct": None,
        "days_held": 0,
        "exit_date": None,
        "exit_price": None,
        "holding_days": None,
        "return_pct": None,
    }


def record_new_signals(
    tracker: Dict[str, Any],
    long_candidates: List[Dict[str, Any]],
    short_candidates: List[Dict[str, Any]],
    today: dt.date,
    price_history_by_ticker: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    """Opens a tracked position for any candidate not already open under the
    same (ticker, signal_type) key. For LONG candidates this is entry_price
    is None until the ticker actually has post-listing bars (see
    update_positions); for SHORT candidates entry_price is today's close,
    looked up from price_history_by_ticker if the candidate dict itself
    doesn't carry current_price.
    """
    price_history_by_ticker = price_history_by_ticker or {}
    open_keys = _open_keys(tracker)

    for c in long_candidates:
        if c.get("direction") != "LONG":
            continue
        key = (c["ticker"], "long_watch")
        if key in open_keys:
            continue
        tracker["positions"].append(
            _new_position(
                ticker=c["ticker"],
                name=c.get("name", ""),
                direction="LONG",
                signal_type="long_watch",
                style="Score-based LONG watch",
                flagged_date=today.isoformat(),
                entry_price=None,
            )
        )
        open_keys.add(key)

    for c in short_candidates:
        for reason in c.get("reasons", []):
            if reason not in ("momentum_fade", "lockup_expiry_watch"):
                continue
            key = (c["ticker"], reason)
            if key in open_keys:
                continue
            entry_price = c.get("current_price")
            if entry_price is None:
                bars = sorted(price_history_by_ticker.get(c["ticker"]) or [], key=lambda b: b["date"])
                if bars:
                    entry_price = bars[-1]["close"]
            tracker["positions"].append(
                _new_position(
                    ticker=c["ticker"],
                    name=c.get("name", ""),
                    direction="SHORT",
                    signal_type=reason,
                    style=c.get("suggested_style", ""),
                    flagged_date=today.isoformat(),
                    entry_price=entry_price,
                )
            )
            open_keys.add(key)

    return tracker


def update_positions(
    tracker: Dict[str, Any],
    price_history_by_ticker: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Re-evaluates every open position against the fullest bar history
    available for its ticker, closing it if the trailing stop has fired or
    its holding window has expired, otherwise just updating its mark.
    """
    for pos in tracker["positions"]:
        if pos["status"] != "open":
            continue

        bars = sorted(price_history_by_ticker.get(pos["ticker"]) or [], key=lambda b: b["date"])
        if not bars:
            continue  # no price data for this ticker yet (e.g. pending pre-listing LONG)

        try:
            entry_idx = next(i for i, b in enumerate(bars) if b["date"] >= pos["flagged_date"])
        except StopIteration:
            continue  # all available bars predate the flag -- shouldn't happen, but be safe

        if pos["entry_price"] is None:
            pos["entry_price"] = bars[entry_idx]["close"]

        closes = [b["close"] for b in bars]
        is_long = pos["direction"] == "LONG"
        hold_days = _HOLD_DAYS_BY_SIGNAL.get(pos["signal_type"], config.POSITION_EXIT_DAY)
        max_index = entry_idx + hold_days
        last_available_index = len(closes) - 1
        scan_limit = min(max_index, last_available_index)

        exit_idx = _trailing_stop_exit_index(closes, entry_idx, scan_limit, is_long=is_long)
        stop_triggered = exit_idx < scan_limit
        window_expired = last_available_index >= max_index

        if stop_triggered or window_expired:
            final_exit_idx = exit_idx if stop_triggered else max_index
            final_exit_idx = min(final_exit_idx, last_available_index)
            entry_price = pos["entry_price"]
            exit_price = closes[final_exit_idx]
            pos["status"] = "closed"
            pos["exit_date"] = bars[final_exit_idx]["date"]
            pos["exit_price"] = exit_price
            pos["holding_days"] = final_exit_idx - entry_idx
            pos["return_pct"] = (
                (exit_price - entry_price) / entry_price
                if is_long
                else (entry_price - exit_price) / entry_price
            )
            pos["current_price"] = exit_price
            pos["unrealized_return_pct"] = None
            pos["days_held"] = pos["holding_days"]
        else:
            entry_price = pos["entry_price"]
            current_price = closes[-1]
            pos["current_price"] = current_price
            pos["unrealized_return_pct"] = (
                (current_price - entry_price) / entry_price
                if is_long
                else (entry_price - current_price) / entry_price
            )
            pos["days_held"] = last_available_index - entry_idx

    return tracker
