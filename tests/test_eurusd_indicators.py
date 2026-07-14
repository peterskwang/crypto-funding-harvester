import pytest

from eurusd_strategy.strategy import indicators


def test_ema_matches_hand_computed_recurrence():
    # length=2 -> alpha=2/3, seeded on the first value (ta.ema semantics)
    out = indicators.ema([1.0, 2.0, 3.0], length=2)
    assert out[0] == pytest.approx(1.0)
    assert out[1] == pytest.approx(2 / 3 * 2 + 1 / 3 * 1)
    assert out[2] == pytest.approx(2 / 3 * 3 + 1 / 3 * out[1])


def test_ema_empty_input():
    assert indicators.ema([], length=5) == []


def test_velocity_series_reaches_steady_state_on_constant_slope():
    # A perfectly linear ramp (slope 1/bar) with lookback=2 settles to a
    # constant velocity of 1 once enough history exists, matching the
    # Pine Script's sum_{i=1..lookback}((close-close[i])/i)/lookback by
    # hand: t=2: ((2-1)/1 + (2-0)/2)/2 = (1+1)/2 = 1.
    closes = [0.0, 1.0, 2.0, 3.0, 4.0]
    velocity = indicators.velocity_series(closes, lookback=2)
    assert velocity[0] == pytest.approx(0.0)  # no history yet
    assert velocity[1] == pytest.approx(0.5)  # partial history (only i=1 term)
    assert velocity[2] == pytest.approx(1.0)
    assert velocity[3] == pytest.approx(1.0)
    assert velocity[4] == pytest.approx(1.0)


def test_velocity_series_flat_prices_is_zero():
    closes = [1.1] * 10
    velocity = indicators.velocity_series(closes, lookback=5)
    assert all(v == pytest.approx(0.0) for v in velocity)


def test_acceleration_series_zero_when_velocity_constant():
    # Steady-state velocity (no change bar-to-bar) implies zero acceleration,
    # since accelerationSum sums (velocity[t]-velocity[t-i])/i.
    velocity = [1.0] * 10
    acceleration = indicators.acceleration_series(velocity, lookback=3)
    assert all(a == pytest.approx(0.0) for a in acceleration[3:])


def test_crossover_fires_exactly_at_threshold_crossing():
    series = [0.0, 0.5, 1.5, 1.6, 0.9]
    crossed = indicators.crossover(series, threshold=1.0)
    assert crossed == [False, False, True, False, False]


def test_crossunder_fires_exactly_at_threshold_crossing():
    series = [2.0, 1.5, 0.5, 0.4, 1.1]
    crossed = indicators.crossunder(series, threshold=1.0)
    assert crossed == [False, False, True, False, False]


def test_volume_delta_proxy_buy_heavy_bar():
    # Close near the high -> mostly buy volume, positive delta.
    bars = [{"high": 10.0, "low": 5.0, "close": 9.0, "volume": 100.0}]
    delta = indicators.volume_delta_proxy(bars)
    buy = 100.0 * (9.0 - 5.0) / 5.0
    sell = 100.0 * (10.0 - 9.0) / 5.0
    assert delta[0] == pytest.approx(buy - sell)
    assert delta[0] > 0


def test_volume_delta_proxy_sell_heavy_bar():
    bars = [{"high": 10.0, "low": 5.0, "close": 6.0, "volume": 100.0}]
    delta = indicators.volume_delta_proxy(bars)
    assert delta[0] < 0


def test_volume_delta_proxy_doji_bar_is_zero_not_division_error():
    bars = [{"high": 7.0, "low": 7.0, "close": 7.0, "volume": 500.0}]
    delta = indicators.volume_delta_proxy(bars)
    assert delta[0] == 0.0


def test_ema_trend_filter_length_uses_config_default():
    closes = list(range(1, 121))
    bars = [{"close": float(c)} for c in closes]
    trend = indicators.ema_trend_filter(bars)
    assert len(trend) == len(bars)
    # A monotonically rising series' EMA should also be monotonically rising.
    assert all(trend[i] <= trend[i + 1] for i in range(len(trend) - 1))
