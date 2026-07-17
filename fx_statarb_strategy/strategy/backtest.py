"""EURUSD/GBPUSD pairs stat-arb backtest engine, versioned v1.0 -> v5.0.

Each version is a concrete config preset below; the changelog documents
the actual flaw each version fixes, in order:

v1.0 (baseline): static hedge ratio fit ONCE on the full backtest window.
  This is a real, deliberate flaw kept visible here rather than smoothed
  over -- a live system on day 1 cannot know a beta fit using data from
  three months in the future. It's included as the honest starting point,
  not a strawman.

v2.0: adds a quantified regime filter (Lo-MacKinlay variance ratio test)
  so entries only fire when the spread is statistically mean-reverting
  over the recent window, not trending. Same static full-sample beta as
  v1.0 -- isolates the effect of the regime filter alone.

v3.0: adds an event-driven blackout around scheduled high-impact EUR/GBP/USD
  macro releases, when correlation-breakdown risk is elevated. Same beta
  and regime filter as v2.0 -- isolates the effect of the event filter.

v4.0: replaces the static full-sample beta with a rolling, strictly
  backward-looking beta (no lookahead) and adds volatility-targeted
  position sizing. This is where the v1.0 lookahead flaw actually gets
  fixed.

v5.0: combines all of the above and is evaluated with a proper in-sample
  (calibration) / out-of-sample (untouched validation) split, the same
  discipline used for the EURUSD EMA strategy -- because a strategy that
  only works in-sample isn't a strategy, it's a fitted curve.

P&L convention: a position is "long the spread" (long EURUSD notional,
short beta*GBPUSD notional) or "short the spread" (the reverse). Since the
spread is defined in log-price space (log EURUSD - beta*log GBPUSD), the
log-return of a long-spread position over the holding period is
approximately (spread_exit - spread_entry), using the beta fixed at entry
for the life of the trade (standard pairs-backtest convention -- the hedge
is not continuously rebalanced intra-trade).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from fx_statarb_strategy import config
from fx_statarb_strategy.strategy import pairs


def _closes(bars: List[dict]) -> List[float]:
    return [b["close"] for b in bars]


def build_signals(
    eur_bars: List[dict],
    gbp_bars: List[dict],
    beta_mode: str = "static_full",
    fixed_beta: Optional[float] = None,
    hedge_lookback: Optional[int] = None,
    hedge_update_every: Optional[int] = None,
    hedge_ewma_alpha: Optional[float] = "default",
    zscore_lookback: Optional[int] = None,
    regime_filter: bool = False,
    regime_lookback: Optional[int] = None,
    regime_vr_k: Optional[int] = None,
    regime_vr_threshold: Optional[float] = None,
) -> Dict[str, list]:
    eur_closes = _closes(eur_bars)
    gbp_closes = _closes(gbp_bars)
    zscore_lookback = zscore_lookback or config.ZSCORE_LOOKBACK_BARS

    if beta_mode == "static_fixed":
        # beta supplied by the caller (e.g. fit once on in-sample data only,
        # for walk-forward validation -- see run_backtest's min_entry_index).
        beta_series = [fixed_beta] * len(eur_closes)
    elif beta_mode == "static_full":
        beta = pairs.static_hedge_ratio(eur_closes, gbp_closes)
        beta_series = [beta] * len(eur_closes)
    elif beta_mode == "rolling":
        hedge_lookback = hedge_lookback or config.HEDGE_RATIO_LOOKBACK_BARS
        hedge_update_every = hedge_update_every or config.HEDGE_RATIO_UPDATE_EVERY_BARS
        alpha = config.HEDGE_RATIO_EWMA_ALPHA if hedge_ewma_alpha == "default" else hedge_ewma_alpha
        beta_series = pairs.rolling_hedge_ratios(
            eur_closes, gbp_closes, hedge_lookback, update_every=hedge_update_every, ewma_alpha=alpha
        )
    else:
        raise ValueError(f"unknown beta_mode {beta_mode!r}")

    spread = pairs.spread_series(eur_closes, gbp_closes, beta_series)
    zscore = pairs.rolling_zscore(spread, zscore_lookback)

    regime_ok = [True] * len(eur_closes)
    if regime_filter:
        regime_lookback = regime_lookback or config.REGIME_LOOKBACK_BARS
        regime_vr_k = regime_vr_k or config.REGIME_VR_K
        regime_vr_threshold = regime_vr_threshold if regime_vr_threshold is not None else config.REGIME_VR_THRESHOLD
        for t in range(regime_lookback, len(spread)):
            window = [s for s in spread[t - regime_lookback:t] if s is not None]
            if len(window) < regime_lookback // 2:
                regime_ok[t] = False
                continue
            vr = pairs.variance_ratio(window, regime_vr_k)
            regime_ok[t] = vr is not None and vr < regime_vr_threshold

    return {"beta": beta_series, "spread": spread, "zscore": zscore, "regime_ok": regime_ok}


def run_backtest(
    eur_bars: List[dict],
    gbp_bars: List[dict],
    beta_mode: str = "static_full",
    fixed_beta: Optional[float] = None,
    hedge_lookback: Optional[int] = None,
    hedge_update_every: Optional[int] = None,
    hedge_ewma_alpha: Optional[float] = "default",
    zscore_lookback: Optional[int] = None,
    entry_zscore: Optional[float] = None,
    exit_zscore: Optional[float] = None,
    stop_zscore: Optional[float] = None,
    max_hold_bars: Optional[int] = None,
    regime_filter: bool = False,
    event_blackout_bars: Optional[set] = None,
    vol_target_sizing: bool = False,
    vol_lookback: Optional[int] = None,
    min_entry_index: int = 0,
) -> List[Dict[str, Any]]:
    """Walks the aligned bar series once, one pairs-position at a time.
    event_blackout_bars: a set of bar indices during which new entries are
    blocked (v3.0+; computed by strategy.events and passed in).
    vol_target_sizing (v4.0+): scales each trade's return by an inverse-vol
    weight (normalized to mean 1 across all trades) so trades entered
    during calmer spread regimes aren't diluted to the same size as trades
    entered during turbulent ones -- a fixed dollar bet in a wide-spread
    regime carries more risk than the same bet in a tight one.
    min_entry_index (v5.0 walk-forward validation): blocks any new entry
    before this bar index, so the same call can compute rolling stats over
    the full series (needed for zscore/regime warmup) while only actually
    trading the out-of-sample portion."""
    entry_zscore = entry_zscore if entry_zscore is not None else config.ENTRY_ZSCORE
    exit_zscore = exit_zscore if exit_zscore is not None else config.EXIT_ZSCORE
    stop_zscore = stop_zscore if stop_zscore is not None else config.STOP_ZSCORE
    max_hold_bars = max_hold_bars if max_hold_bars is not None else config.MAX_HOLD_BARS
    event_blackout_bars = event_blackout_bars or set()

    signals = build_signals(
        eur_bars, gbp_bars,
        beta_mode=beta_mode, fixed_beta=fixed_beta, hedge_lookback=hedge_lookback,
        hedge_update_every=hedge_update_every, hedge_ewma_alpha=hedge_ewma_alpha,
        zscore_lookback=zscore_lookback,
        regime_filter=regime_filter,
    )
    spread = signals["spread"]
    zscore = signals["zscore"]
    regime_ok = signals["regime_ok"]
    beta_series = signals["beta"]
    eur_closes = _closes(eur_bars)
    gbp_closes = _closes(gbp_bars)
    dates = [b["date"] for b in eur_bars]
    n = len(eur_bars)
    vol_lookback = vol_lookback or config.ZSCORE_LOOKBACK_BARS

    def _recent_spread_vol(index: int) -> Optional[float]:
        window = [s for s in spread[max(0, index - vol_lookback):index] if s is not None]
        if len(window) < 2:
            return None
        diffs = [window[i] - window[i - 1] for i in range(1, len(window))]
        mean = sum(diffs) / len(diffs)
        var = sum((d - mean) ** 2 for d in diffs) / len(diffs)
        return var ** 0.5

    trades: List[Dict[str, Any]] = []
    t = max(0, min_entry_index)
    while t < n - 1:
        z = zscore[t]
        if z is None or spread[t] is None or not regime_ok[t] or t in event_blackout_bars:
            t += 1
            continue

        direction = None
        if z >= entry_zscore:
            direction = "SHORT_SPREAD"   # spread too high -> bet it falls
        elif z <= -entry_zscore:
            direction = "LONG_SPREAD"    # spread too low -> bet it rises

        if direction is None:
            t += 1
            continue

        entry_index = t + 1  # enter at next bar's open-equivalent (next bar's spread), avoiding same-bar lookahead
        if spread[entry_index] is None:
            t += 1
            continue

        entry_spread = spread[entry_index]
        entry_beta = beta_series[entry_index] if isinstance(beta_series, list) else beta_series
        max_index = min(entry_index + max_hold_bars, n - 1)
        sign = 1 if direction == "LONG_SPREAD" else -1

        exit_index = entry_index
        exit_reason = "max_hold"
        for i in range(entry_index + 1, max_index + 1):
            zi = zscore[i]
            if zi is None:
                continue
            if abs(zi) >= stop_zscore:
                exit_index = i
                exit_reason = "stop_loss"
                break
            if abs(zi) <= exit_zscore:
                exit_index = i
                exit_reason = "reversion"
                break
        else:
            exit_index = max_index
            exit_reason = "max_hold"

        if entry_beta is None:
            t = exit_index + 1
            continue

        # P&L must use the beta FIXED at entry, not spread[exit_index] (which
        # reflects whatever beta is current at that later bar under
        # beta_mode="rolling"). A real position holds fixed notional from
        # entry to exit; reading a time-varying spread series for P&L was a
        # real bug found in v4.0 development -- it silently mixed "the
        # hedge ratio changed" into "the trade made/lost money," producing
        # phantom double-digit-percent swings with no corresponding z-score
        # move. exit_zscore/stop/reversion decisions still correctly use
        # the live (time-varying) z-score, since that's what a real system
        # watching the spread in real time would see.
        exit_spread_at_entry_beta = math.log(eur_closes[exit_index]) - entry_beta * math.log(gbp_closes[exit_index])
        return_pct = sign * (exit_spread_at_entry_beta - entry_spread)
        entry_vol = _recent_spread_vol(entry_index)

        trades.append({
            "direction": direction,
            "signal_date": dates[t],
            "entry_date": dates[entry_index],
            "entry_zscore": round(z, 3),
            "entry_beta": round(entry_beta, 4) if entry_beta else None,
            "exit_date": dates[exit_index],
            "exit_zscore": round(zscore[exit_index], 3) if zscore[exit_index] is not None else None,
            "exit_reason": exit_reason,
            "holding_bars": exit_index - entry_index,
            "return_pct": return_pct,
            "raw_return_pct": return_pct,
            "entry_vol": entry_vol,
            "size_weight": 1.0,
        })

        t = exit_index + 1  # no overlapping trades

    if vol_target_sizing:
        vols = [tr["entry_vol"] for tr in trades if tr["entry_vol"]]
        if vols:
            avg_inv_vol = sum(1.0 / v for v in vols) / len(vols)
            for tr in trades:
                if tr["entry_vol"]:
                    raw_weight = (1.0 / tr["entry_vol"]) / avg_inv_vol
                    weight = min(max(raw_weight, 0.3), 3.0)  # cap extreme leverage either direction
                else:
                    weight = 1.0
                tr["size_weight"] = round(weight, 3)
                tr["return_pct"] = tr["raw_return_pct"] * weight

    return trades


def summarize_trades(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not trades:
        return {"count": 0}

    returns = [t["return_pct"] for t in trades]
    wins = [r for r in returns if r > 0]
    equity = config.INITIAL_CAPITAL
    peak = equity
    max_drawdown = 0.0
    for r in returns:
        equity *= (1 + r)
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak)

    reasons = {}
    for t in trades:
        reasons[t["exit_reason"]] = reasons.get(t["exit_reason"], 0) + 1

    return {
        "count": len(trades),
        "win_rate": len(wins) / len(trades),
        "avg_return": sum(returns) / len(trades),
        "total_return": sum(returns),
        "final_equity": equity,
        "max_drawdown": max_drawdown,
        "exit_reasons": reasons,
        "best_trade": max(trades, key=lambda t: t["return_pct"]),
        "worst_trade": min(trades, key=lambda t: t["return_pct"]),
    }
