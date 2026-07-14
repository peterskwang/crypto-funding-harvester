import datetime as dt

import pytest

from eurusd_strategy.strategy.backtest import (
    _bracket_exit,
    _trailing_stop_exit_index,
    run_backtest,
    summarize_trades,
)


def _bars(closes, opens=None, highs=None, lows=None, volumes=None, start_date=dt.date(2026, 1, 2)):
    n = len(closes)
    opens = opens or closes
    highs = highs or [max(o, c) for o, c in zip(opens, closes)]
    lows = lows or [min(o, c) for o, c in zip(opens, closes)]
    volumes = volumes or [1000.0] * n
    return [
        {
            "date": (start_date + dt.timedelta(days=i)).isoformat(),
            "open": opens[i],
            "high": highs[i],
            "low": lows[i],
            "close": closes[i],
            "volume": volumes[i],
        }
        for i in range(n)
    ]


def test_trailing_stop_exit_index_long_triggers_on_pullback():
    closes = [10.0, 11.0, 12.0, 13.0, 11.5]  # peak 13, pulls back to 11.5 (>10%)
    exit_index = _trailing_stop_exit_index(closes, start_index=0, max_index=4, is_long=True, pct=0.10)
    assert exit_index == 4


def test_trailing_stop_exit_index_long_clamps_to_max_when_never_triggered():
    closes = [10.0, 10.5, 10.8, 10.9]  # never pulls back 10% from peak
    exit_index = _trailing_stop_exit_index(closes, start_index=0, max_index=3, is_long=True, pct=0.10)
    assert exit_index == 3


def test_trailing_stop_exit_index_short_triggers_on_bounce():
    closes = [10.0, 9.0, 8.0, 8.9]  # low 8.0, bounces to 8.9 (>10% above low)
    exit_index = _trailing_stop_exit_index(closes, start_index=0, max_index=3, is_long=False, pct=0.10)
    assert exit_index == 3


def test_run_backtest_no_signals_produces_no_trades():
    # Flat prices never cross any velocity threshold.
    bars = _bars([1.1] * 60)
    trades = run_backtest(bars, use_ema_filter=False, use_delta_filter=False)
    assert trades == []


def test_run_backtest_entry_uses_next_bar_open_not_signal_bar_close():
    # Construct a price path that ramps steadily enough to fire strong_up,
    # then verify every trade's entry_date is strictly after its signal_date
    # implicitly (entry_price is bars[t+1]['open'], not bars[t]['close']).
    closes = [1.10 + 0.002 * i for i in range(60)]
    bars = _bars(closes)
    trades = run_backtest(bars, use_ema_filter=False, use_delta_filter=False)
    for t in trades:
        assert t["entry_date"] > t["signal_date"]


def test_run_backtest_trades_do_not_overlap():
    closes = [1.10 + 0.003 * i for i in range(120)]
    bars = _bars(closes)
    trades = run_backtest(bars, use_ema_filter=False, use_delta_filter=False, max_hold_days=5)
    for a, b in zip(trades, trades[1:]):
        assert b["entry_date"] > a["exit_date"]


def test_bracket_exit_long_hits_take_profit():
    bars = _bars(
        closes=[10.0, 10.6, 10.4],
        highs=[10.0, 10.6, 10.4],
        lows=[10.0, 10.4, 10.2],
    )
    # entry_price=10.0, tp=5% -> 10.5; bar 1's high (10.6) reaches it first.
    exit_index, exit_price = _bracket_exit(bars, entry_index=0, max_index=2, is_long=True,
                                            entry_price=10.0, tp_pct=0.05, sl_pct=0.02)
    assert exit_index == 1
    assert exit_price == pytest.approx(10.5)


def test_bracket_exit_long_hits_stop_loss():
    bars = _bars(
        closes=[10.0, 9.7, 9.5],
        highs=[10.0, 9.8, 9.6],
        lows=[10.0, 9.6, 9.4],
    )
    # entry_price=10.0, sl=2% -> 9.8; bar 1's low (9.6) breaches it.
    exit_index, exit_price = _bracket_exit(bars, entry_index=0, max_index=2, is_long=True,
                                            entry_price=10.0, tp_pct=0.05, sl_pct=0.02)
    assert exit_index == 1
    assert exit_price == pytest.approx(9.8)


def test_bracket_exit_same_bar_ambiguity_resolves_to_stop_loss():
    # A single wide bar whose range spans both the TP and SL levels --
    # intrabar order is unknowable from daily OHLC, so SL is assumed to win.
    bars = _bars(closes=[10.0, 10.0], highs=[10.0, 11.0], lows=[10.0, 9.0])
    exit_index, exit_price = _bracket_exit(bars, entry_index=0, max_index=1, is_long=True,
                                            entry_price=10.0, tp_pct=0.05, sl_pct=0.05)
    assert exit_index == 1
    assert exit_price == pytest.approx(9.5)  # the SL level, not the TP level


def test_bracket_exit_never_triggers_clamps_to_max_index_close():
    bars = _bars(closes=[10.0, 10.05, 10.08], highs=[10.0, 10.05, 10.08], lows=[10.0, 10.04, 10.07])
    exit_index, exit_price = _bracket_exit(bars, entry_index=0, max_index=2, is_long=True,
                                            entry_price=10.0, tp_pct=0.05, sl_pct=0.05)
    assert exit_index == 2
    assert exit_price == pytest.approx(10.08)  # falls back to the bar's close


def test_bracket_exit_short_direction_mirrors_long():
    bars = _bars(
        closes=[10.0, 9.4, 9.6],
        highs=[10.0, 9.6, 9.7],
        lows=[10.0, 9.3, 9.5],
    )
    # short entry_price=10.0, tp=5% -> 9.5; bar 1's low (9.3) reaches it.
    exit_index, exit_price = _bracket_exit(bars, entry_index=0, max_index=2, is_long=False,
                                            entry_price=10.0, tp_pct=0.05, sl_pct=0.02)
    assert exit_index == 1
    assert exit_price == pytest.approx(9.5)


def test_run_backtest_bracket_mode_uses_config_defaults_when_unspecified():
    closes = [1.10 + 0.01 * i for i in range(30)]
    bars = _bars(closes)
    trades = run_backtest(bars, use_ema_filter=False, use_delta_filter=False, exit_mode="bracket")
    # Just confirming it runs end-to-end without error and returns trades
    # shaped like the trailing-mode ones.
    for t in trades:
        assert "return_pct" in t and "exit_price" in t


def test_summarize_trades_empty():
    assert summarize_trades([]) == {"count": 0}


def test_summarize_trades_computes_win_rate_and_drawdown():
    trades = [
        {"direction": "LONG", "return_pct": 0.05},
        {"direction": "LONG", "return_pct": -0.02},
        {"direction": "SHORT", "return_pct": 0.03},
    ]
    summary = summarize_trades(trades)
    assert summary["count"] == 3
    assert summary["overall"]["win_rate"] == pytest.approx(2 / 3)
    assert summary["long"]["count"] == 2
    assert summary["short"]["count"] == 1
    assert summary["max_drawdown"] >= 0
