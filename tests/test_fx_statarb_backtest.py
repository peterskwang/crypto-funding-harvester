import datetime as dt
import math

import pytest

from fx_statarb_strategy.strategy import backtest


def _bars(closes, start=dt.datetime(2026, 1, 1), step_minutes=15):
    return [
        {"date": (start + dt.timedelta(minutes=step_minutes * i)).strftime("%Y-%m-%d %H:%M:%S"), "close": c}
        for i, c in enumerate(closes)
    ]


def _synthetic_pair_with_excursion(n=900, spike_center=410, spike_half_width=10, spike_height=0.004):
    """A pair series with tiny pseudo-noise plus one deliberate, reverting
    excursion -- reliably crosses ENTRY_ZSCORE without the amplitude
    cancelling itself out the way a uniform periodic oscillation would
    (z-scores are scale-invariant to a wiggle that's present throughout the
    whole rolling window, since numerator and denominator scale together)."""
    gbp = [1.30 + 0.00003 * ((i * 37) % 17 - 8) for i in range(n)]
    eur = [1.10 + 1.0 * (g - 1.30) + 0.00003 * ((i * 53) % 13 - 6) for i, g in enumerate(gbp)]
    for i in range(spike_center - spike_half_width, spike_center + spike_half_width):
        eur[i] += spike_height * (1 - abs(i - spike_center) / spike_half_width)
    return eur, gbp


def test_summarize_trades_empty():
    assert backtest.summarize_trades([]) == {"count": 0}


def test_summarize_trades_computes_stats_and_drawdown():
    trades = [
        {"return_pct": 0.01, "exit_reason": "reversion"},
        {"return_pct": -0.005, "exit_reason": "stop_loss"},
        {"return_pct": 0.02, "exit_reason": "reversion"},
    ]
    s = backtest.summarize_trades(trades)
    assert s["count"] == 3
    assert s["win_rate"] == pytest.approx(2 / 3)
    assert s["exit_reasons"] == {"reversion": 2, "stop_loss": 1}
    assert s["max_drawdown"] >= 0


def test_run_backtest_no_signal_produces_no_trades():
    # Perfectly flat, identical closes -> spread never moves -> zscore
    # windows have zero variance -> no z-score ever computed -> no entries.
    n = 700
    eur = _bars([1.10] * n)
    gbp = _bars([1.30] * n)
    trades = backtest.run_backtest(eur, gbp, beta_mode="static_full")
    assert trades == []


def test_run_backtest_min_entry_index_blocks_early_entries():
    # A synthetic spread with a deliberate excursion around bar 410;
    # with min_entry_index set past that point, the entry it would have
    # produced must be blocked.
    eur, gbp = _synthetic_pair_with_excursion(n=900, spike_center=410)
    eur_bars = _bars(eur)
    gbp_bars = _bars(gbp)

    all_trades = backtest.run_backtest(eur_bars, gbp_bars, beta_mode="static_full")
    assert len(all_trades) > 0  # sanity: this synthetic series does generate trades

    split = 500
    split_date = eur_bars[split]["date"]
    restricted = backtest.run_backtest(eur_bars, gbp_bars, beta_mode="static_full", min_entry_index=split)
    for t in restricted:
        assert t["entry_date"] >= split_date
    assert len(restricted) < len(all_trades)  # the pre-split excursion trade(s) got dropped


def test_run_backtest_fixed_beta_pnl_ignores_later_beta_drift():
    # Regression test for the real v4.0 bug: P&L must be computed using the
    # beta fixed at entry, not whatever beta_series says at the exit bar.
    # Build a case with beta_mode="rolling" where beta clearly drifts, and
    # confirm the trade's return_pct is consistent with a FIXED-beta
    # recomputation rather than the live (drifting) spread series.
    n = 700
    gbp = [1.30 + 0.0002 * i for i in range(n)]
    # true relationship is stable (eur tracks 1.0x gbp movement) but noisy
    # early beta estimates will differ, exercising real EWMA drift
    eur = [1.10 + 1.0 * (g - 1.30) for g in gbp]
    # add a deliberate wiggle so entries actually fire
    for i in range(n):
        eur[i] += 0.0015 * math.sin(i / 6)

    eur_bars = _bars(eur)
    gbp_bars = _bars(gbp)
    trades = backtest.run_backtest(eur_bars, gbp_bars, beta_mode="rolling", hedge_lookback=200, hedge_ewma_alpha=0.05)

    for t in trades:
        entry_i = next(i for i, b in enumerate(eur_bars) if b["date"] == t["entry_date"])
        exit_i = next(i for i, b in enumerate(eur_bars) if b["date"] == t["exit_date"])
        entry_beta = t["entry_beta"]
        entry_spread = math.log(eur_bars[entry_i]["close"]) - entry_beta * math.log(gbp_bars[entry_i]["close"])
        exit_spread_fixed = math.log(eur_bars[exit_i]["close"]) - entry_beta * math.log(gbp_bars[exit_i]["close"])
        sign = 1 if t["direction"] == "LONG_SPREAD" else -1
        expected_return = sign * (exit_spread_fixed - entry_spread)
        assert t["return_pct"] == pytest.approx(expected_return, abs=1e-9)


def test_vol_target_sizing_normalizes_weights_around_one():
    eur, gbp = _synthetic_pair_with_excursion(n=900, spike_center=300)
    eur_bars = _bars(eur)
    gbp_bars = _bars(gbp)

    trades = backtest.run_backtest(eur_bars, gbp_bars, beta_mode="static_full", vol_target_sizing=True)
    assert len(trades) > 0
    weights = [t["size_weight"] for t in trades]
    avg_weight = sum(weights) / len(weights)
    assert avg_weight == pytest.approx(1.0, abs=0.5)  # normalized around 1, not a hard equality
    assert all(0.3 <= w <= 3.0 for w in weights)  # capped range
