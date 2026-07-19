import pytest

from crypto_trend_strategy.strategy import backtest


def _bars(closes, start="2020-01-01"):
    import datetime as dt
    start_d = dt.date.fromisoformat(start)
    return [{"date": (start_d + dt.timedelta(days=i)).isoformat(), "close": c} for i, c in enumerate(closes)]


def test_summarize_empty_curve():
    assert backtest.summarize({"equity_curve": [], "daily_records": [], "trade_log": []}) == {"count": 0}


def test_run_backtest_flat_prices_no_trades_no_pnl():
    # Perfectly flat prices -> zero vol -> no momentum signal ever computed
    # -> equity should stay at initial capital (minus nothing, no trades).
    closes = [100.0] * 260
    bars = {"BTCUSD": _bars(closes)}
    from crypto_trend_strategy.strategy import data
    calendar = data.common_calendar(bars)
    result = backtest.run_backtest(bars, calendar)
    summary = backtest.summarize(result)
    assert summary["total_return"] == pytest.approx(0.0, abs=1e-9)
    assert summary["n_stop_losses"] == 0


def test_run_backtest_single_asset_uptrend_is_profitable_net_of_costs():
    closes = [100.0 * (1.003 ** i) + 0.01 * (i % 3) for i in range(400)]
    bars = {"BTCUSD": _bars(closes)}
    from crypto_trend_strategy.strategy import data
    calendar = data.common_calendar(bars)
    result = backtest.run_backtest(bars, calendar)
    summary = backtest.summarize(result)
    assert summary["total_return"] > 0


def test_run_backtest_stop_loss_triggers_on_sudden_crash():
    # A gradual uptrend establishes a long entry, then a SUDDEN single-day
    # -30% crash -- fast enough that the slow 30/90/200d momentum blend
    # hasn't flipped yet, so the fixed-pct stop must be what exits the
    # position (a gradual decline instead lets the signal itself flip
    # first, which is correct behavior but doesn't exercise the stop --
    # see the backtest module docstring on why the stop is a backstop).
    up = [100.0 * (1.002 ** i) + 0.01 * (i % 3) for i in range(220)]
    crash_price = up[-1] * 0.70
    closes = up + [crash_price, crash_price * 1.005, crash_price * 0.995]
    bars = {"BTCUSD": _bars(closes)}
    from crypto_trend_strategy.strategy import data
    calendar = data.common_calendar(bars)
    result = backtest.run_backtest(bars, calendar)
    summary = backtest.summarize(result)
    assert summary["n_stop_losses"] >= 1
    stop = result["trade_log"][0]
    assert stop["event"] == "stop_loss"
    assert stop["direction"] == "LONG"
    assert stop["return_pct"] < -backtest.config.STOP_LOSS_PCT + 1e-6


def test_run_backtest_gross_exposure_respects_cap():
    import random
    random.seed(3)
    n = 400
    bars = {}
    from crypto_trend_strategy.strategy import data
    for sym in ["BTCUSD", "ETHUSD", "SOLUSD"]:
        closes = [100.0 * (1.003 ** i) + 0.02 * ((i * 7) % 5 - 2) for i in range(n)]
        bars[sym] = _bars(closes)
    calendar = data.common_calendar(bars)
    result = backtest.run_backtest(bars, calendar, gross_exposure_cap=1.5)
    for point in result["equity_curve"]:
        assert point["gross_exposure"] <= 1.5 + 1e-6


def test_run_backtest_start_end_date_filters_curve():
    closes = [100.0 * (1.002 ** i) + 0.01 * (i % 3) for i in range(400)]
    bars = {"BTCUSD": _bars(closes, start="2020-01-01")}
    from crypto_trend_strategy.strategy import data
    calendar = data.common_calendar(bars)
    result = backtest.run_backtest(bars, calendar, start_date="2020-06-01", end_date="2020-12-01")
    dates = [p["date"] for p in result["equity_curve"]]
    assert all("2020-06-01" <= d <= "2020-12-01" for d in dates)
