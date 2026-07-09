import datetime as dt

import pytest

from pre_ipo_screener.screener.backtest import (
    run_backtest,
    simulate_long_trade,
    simulate_lockup_short_trade,
    simulate_momentum_fade_trade,
    summarize_trades,
)


def _bars(closes, opens=None, start_date=dt.date(2026, 1, 2)):
    opens = opens or closes
    return [
        {"date": (start_date + dt.timedelta(days=i)).isoformat(), "o": opens[i], "c": closes[i]}
        for i in range(len(closes))
    ]


def test_simulate_long_trade_intraday_style():
    bars = _bars(closes=[11.0, 12.1, 13.0, 13.5])  # entry idx0, exit idx1 (INTRADAY_EXIT_DAY=1)

    trade = simulate_long_trade({"ticker": "ACRB", "name": "Acme Robotics"}, bars, "Day 1-2 momentum trade (high volatility, short hold)")

    assert trade["entry_price"] == 11.0
    assert trade["exit_price"] == 12.1
    assert trade["return_pct"] == pytest.approx(0.1, rel=1e-3)
    assert trade["direction"] == "LONG"


def test_simulate_long_trade_swing_style():
    closes = [10 + i * 0.5 for i in range(16)]  # index 15 -> 17.5 (SWING_EXIT_DAY=15)
    bars = _bars(closes)

    trade = simulate_long_trade({"ticker": "SWNG", "name": "Swing Co"}, bars, "2-4 week swing hold")

    assert trade["entry_price"] == 10.0
    assert trade["exit_price"] == pytest.approx(17.5)
    assert trade["return_pct"] == pytest.approx(0.75, rel=1e-3)


def test_simulate_long_trade_position_style_clamps_to_available_bars():
    closes = list(range(10, 40))  # only 30 bars, POSITION_EXIT_DAY=42 exceeds available history
    bars = _bars([float(c) for c in closes])

    trade = simulate_long_trade({"ticker": "POSN", "name": "Position Co"}, bars, "Position hold (low volatility, longer horizon)")

    assert trade["holding_days"] == len(bars) - 1
    assert trade["exit_price"] == closes[-1]


def test_simulate_momentum_fade_trade_shorts_the_peak():
    closes = [10, 15, 20, 18, 16, 14, 13, 12, 11, 10, 9, 8]  # peak at index 2, MOMENTUM_FADE_HOLD_DAYS=10
    bars = _bars([float(c) for c in closes])

    trade = simulate_momentum_fade_trade({"ticker": "HOTX", "name": "Hot Co"}, bars)

    assert trade["direction"] == "SHORT"
    assert trade["entry_price"] == 20.0
    assert trade["exit_price"] == 8.0  # clamped to last available bar (index 11)
    assert trade["return_pct"] == pytest.approx(0.6, rel=1e-3)  # profit since price fell


def test_simulate_lockup_short_trade_requires_enough_history():
    short_bars = _bars([float(200 - i) for i in range(50)])  # only 50 trading days, lockup entry needs 90

    assert simulate_lockup_short_trade({"ticker": "SHRT", "name": "Short Co"}, short_bars) is None


def test_simulate_lockup_short_trade_computes_return():
    closes = [float(200 - i) for i in range(130)]  # entry idx90=110, exit idx120=80
    bars = _bars(closes)

    trade = simulate_lockup_short_trade({"ticker": "LOCK", "name": "Lockup Co"}, bars)

    assert trade["entry_price"] == 110.0
    assert trade["exit_price"] == 80.0
    assert trade["return_pct"] == pytest.approx(30 / 110, rel=1e-3)
    assert trade["holding_days"] == 30


def test_summarize_trades_computes_win_rate_and_best_worst():
    trades = [
        {"ticker": "A", "direction": "LONG", "return_pct": 0.10},
        {"ticker": "B", "direction": "LONG", "return_pct": -0.05},
        {"ticker": "C", "direction": "SHORT", "return_pct": 0.20},
    ]

    summary = summarize_trades(trades)

    assert summary["count"] == 3
    assert summary["overall"]["win_rate"] == pytest.approx(2 / 3)
    assert summary["long"]["count"] == 2
    assert summary["short"]["count"] == 1
    assert summary["best_trade"]["ticker"] == "C"
    assert summary["worst_trade"]["ticker"] == "B"


def test_summarize_trades_handles_empty_list():
    assert summarize_trades([]) == {"count": 0}


def test_run_backtest_produces_trades_without_lookahead_errors():
    # Two candidates, second listed later -- its analog pool should include the first.
    early_bars = _bars([10.0, 11.0, 12.0, 20.0], start_date=dt.date(2026, 1, 2))
    late_bars = _bars([10.0, 11.5, 12.5, 21.0], start_date=dt.date(2026, 3, 2))

    candidates = [
        {
            "ticker": "EARLY", "name": "Early Co", "listing_date": "2026-01-02",
            "total_offer_size": 500_000_000, "sector_tag": "TECH",
            "day1_pop": 0.10, "decay_from_high": None, "realized_volatility": 0.02,
            "bars": early_bars,
        },
        {
            "ticker": "LATE", "name": "Late Co", "listing_date": "2026-03-02",
            "total_offer_size": 500_000_000, "sector_tag": "TECH",
            "day1_pop": 0.15, "decay_from_high": None, "realized_volatility": 0.02,
            "bars": late_bars,
        },
    ]

    trades = run_backtest(candidates)

    assert isinstance(trades, list)
    tickers_traded = {t["ticker"] for t in trades}
    assert tickers_traded <= {"EARLY", "LATE"}
