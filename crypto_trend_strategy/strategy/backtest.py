"""Multi-asset vol-targeted trend-following portfolio backtest.

Daily rebalance: each asset's target weight comes from its own momentum
signal x vol-target sizing (see signals.py), portfolio-scaled to a gross
exposure cap. Positions are held from one day's close to the next day's
close (yesterday's weight earns today's return -- no lookahead). A
stop-loss is tracked per-asset since each position's last entry; once
breached, that asset is forced flat and put in cooldown until its
momentum signal actually changes (not just re-crossing the same level),
so a stopped-out position can't immediately re-enter on the same noise
that triggered the stop.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from crypto_trend_strategy import config
from crypto_trend_strategy.strategy import signals


def build_universe_signals(all_bars: Dict[str, List[dict]]) -> Dict[str, dict]:
    out = {}
    for symbol, bars in all_bars.items():
        if len(bars) < config.MIN_HISTORY_DAYS:
            continue
        sig = signals.compute_asset_signals(bars)
        sig["dates"] = [b["date"][:10] for b in bars]
        out[symbol] = sig
    return out


def run_backtest(
    all_bars: Dict[str, List[dict]],
    calendar: List[str],
    gross_exposure_cap: Optional[float] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    gross_exposure_cap = gross_exposure_cap if gross_exposure_cap is not None else config.GROSS_EXPOSURE_CAP
    universe = build_universe_signals(all_bars)
    # date -> {symbol: index into that symbol's arrays}
    date_index: Dict[str, Dict[str, int]] = {}
    for symbol, sig in universe.items():
        for i, d in enumerate(sig["dates"]):
            date_index.setdefault(d, {})[symbol] = i

    trading_dates = [d for d in calendar if (not start_date or d >= start_date) and (not end_date or d <= end_date)]

    equity = config.INITIAL_CAPITAL
    equity_curve = []
    prev_weight: Dict[str, float] = {s: 0.0 for s in universe}
    entry_price: Dict[str, Optional[float]] = {s: None for s in universe}
    entry_direction: Dict[str, int] = {s: 0 for s in universe}
    cooldown_direction: Dict[str, Optional[int]] = {s: None for s in universe}  # direction that must change before re-entry after a stop
    daily_records = []
    trade_log = []

    for d_idx, date in enumerate(trading_dates):
        today_idx = date_index.get(date, {})

        raw_targets: Dict[str, float] = {}
        for symbol, sig in universe.items():
            i = today_idx.get(symbol)
            if i is None:
                raw_targets[symbol] = 0.0
                continue
            direction = sig["direction"][i]
            raw_w = sig["raw_weight"][i]
            close = sig["closes"][i]

            if direction is None or raw_w is None:
                raw_targets[symbol] = 0.0
                continue

            # stop-loss check on the currently held position (if any)
            if prev_weight[symbol] != 0.0 and entry_price[symbol]:
                pos_dir = 1 if prev_weight[symbol] > 0 else -1
                adverse_move = (close - entry_price[symbol]) / entry_price[symbol] * pos_dir
                if adverse_move <= -config.STOP_LOSS_PCT:
                    trade_log.append({
                        "symbol": symbol, "date": date, "event": "stop_loss",
                        "entry_price": entry_price[symbol], "exit_price": close,
                        "direction": "LONG" if pos_dir == 1 else "SHORT",
                        "return_pct": adverse_move,
                    })
                    raw_targets[symbol] = 0.0
                    cooldown_direction[symbol] = pos_dir
                    entry_price[symbol] = None
                    continue

            # cooldown: after a stop, block re-entry in the same direction
            # until the signal's direction actually changes
            if cooldown_direction[symbol] is not None:
                if direction == cooldown_direction[symbol]:
                    raw_targets[symbol] = 0.0
                    continue
                else:
                    cooldown_direction[symbol] = None  # signal changed, cooldown lifted

            raw_targets[symbol] = raw_w

        gross = sum(abs(w) for w in raw_targets.values())
        scale = min(1.0, gross_exposure_cap / gross) if gross > 0 else 1.0
        final_targets = {s: w * scale for s, w in raw_targets.items()}

        # portfolio return for today = yesterday's weights applied to today's return
        port_return = 0.0
        for symbol, sig in universe.items():
            i = today_idx.get(symbol)
            if i is None or i == 0:
                continue
            ret = sig["returns"][i]
            if ret is None:
                continue
            port_return += prev_weight[symbol] * ret

        # transaction costs on turnover (weight changes today)
        turnover = sum(abs(final_targets[s] - prev_weight[s]) for s in universe)
        cost = turnover * config.TRANSACTION_COST_PCT

        equity *= (1 + port_return - cost)
        equity_curve.append({"date": date, "equity": equity, "gross_exposure": gross * scale})
        daily_records.append({"date": date, "port_return": port_return, "cost": cost, "turnover": turnover})

        # update entry tracking for positions that just opened or flipped
        for symbol in universe:
            i = today_idx.get(symbol)
            if i is None:
                continue
            new_w = final_targets[symbol]
            old_w = prev_weight[symbol]
            new_dir = 1 if new_w > 0 else (-1 if new_w < 0 else 0)
            old_dir = 1 if old_w > 0 else (-1 if old_w < 0 else 0)
            if new_dir != 0 and new_dir != old_dir:
                entry_price[symbol] = universe[symbol]["closes"][i]
                entry_direction[symbol] = new_dir

        prev_weight = final_targets

    return {
        "equity_curve": equity_curve,
        "daily_records": daily_records,
        "trade_log": trade_log,
        "universe": list(universe.keys()),
    }


def summarize(result: Dict[str, Any]) -> Dict[str, Any]:
    curve = result["equity_curve"]
    if len(curve) < 2:
        return {"count": 0}

    returns = [r["port_return"] - r["cost"] for r in result["daily_records"]]
    n = len(returns)
    mean_daily = sum(returns) / n
    var_daily = sum((r - mean_daily) ** 2 for r in returns) / n
    std_daily = var_daily ** 0.5

    total_return = curve[-1]["equity"] / config.INITIAL_CAPITAL - 1
    n_years = n / 365
    cagr = (curve[-1]["equity"] / config.INITIAL_CAPITAL) ** (1 / n_years) - 1 if n_years > 0 else None
    annualized_vol = std_daily * (365 ** 0.5)
    sharpe = (mean_daily * 365) / annualized_vol if annualized_vol else None

    peak = config.INITIAL_CAPITAL
    max_dd = 0.0
    for point in curve:
        peak = max(peak, point["equity"])
        dd = (peak - point["equity"]) / peak
        max_dd = max(max_dd, dd)

    return {
        "count": n,
        "start_date": curve[0]["date"],
        "end_date": curve[-1]["date"],
        "total_return": total_return,
        "cagr": cagr,
        "annualized_vol": annualized_vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "n_stop_losses": len([t for t in result["trade_log"] if t["event"] == "stop_loss"]),
        "avg_gross_exposure": sum(c["gross_exposure"] for c in curve) / len(curve),
    }
