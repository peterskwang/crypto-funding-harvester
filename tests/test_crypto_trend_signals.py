import math

import pytest

from crypto_trend_strategy.strategy import signals


def test_daily_returns_basic():
    closes = [100.0, 110.0, 99.0]
    out = signals.daily_returns(closes)
    assert out[0] is None
    assert out[1] == pytest.approx(0.10)
    assert out[2] == pytest.approx((99.0 - 110.0) / 110.0)


def test_realized_vol_flat_series_is_zero():
    closes = [100.0] * 30
    rets = signals.daily_returns(closes)
    vol = signals.realized_vol(rets, lookback=20)
    nonzero = [v for v in vol[20:] if v is not None]
    assert all(v == pytest.approx(0.0) for v in nonzero)


def test_realized_vol_none_when_insufficient_history():
    closes = [100.0, 101.0, 99.0]
    rets = signals.daily_returns(closes)
    vol = signals.realized_vol(rets, lookback=20)
    assert vol[0] is None
    assert vol[1] is None


def test_momentum_composite_uptrend_is_positive():
    # Steady uptrend with tiny noise (pure noiseless trend has zero vol,
    # which would divide-by-zero in the risk-adjustment step).
    closes = [100.0 * (1.001 ** i) + 0.001 * (i % 3) for i in range(250)]
    vol = signals.realized_vol(signals.daily_returns(closes), lookback=20)
    comp = signals.momentum_composite(closes, vol, lookbacks=[30, 90, 200])
    assert comp[200] is not None
    assert comp[200] > 0


def test_momentum_composite_downtrend_is_negative():
    closes = [100.0 * (0.999 ** i) + 0.001 * (i % 3) for i in range(250)]
    vol = signals.realized_vol(signals.daily_returns(closes), lookback=20)
    comp = signals.momentum_composite(closes, vol, lookbacks=[30, 90, 200])
    assert comp[200] is not None
    assert comp[200] < 0


def test_momentum_composite_none_before_max_lookback():
    closes = [100.0 + i for i in range(250)]
    vol = signals.realized_vol(signals.daily_returns(closes), lookback=20)
    comp = signals.momentum_composite(closes, vol, lookbacks=[30, 90, 200])
    assert comp[199] is None  # max lookback is 200, need index >= 200
    assert comp[200] is not None


def test_compute_asset_signals_direction_matches_momentum_sign():
    bars = [{"close": 100.0 * (1.002 ** i) + 0.001 * (i % 3)} for i in range(250)]
    out = signals.compute_asset_signals(bars)
    t = 220
    assert out["momentum"][t] is not None
    if out["momentum"][t] > 0:
        assert out["direction"][t] == 1
    elif out["momentum"][t] < 0:
        assert out["direction"][t] == -1


def test_compute_asset_signals_weight_capped_at_max_asset_weight():
    from crypto_trend_strategy import config
    # Very low volatility -> vol-target sizing would want a huge weight;
    # must be capped at MAX_ASSET_WEIGHT.
    bars = [{"close": 100.0 + 0.0001 * i + 0.00001 * (i % 3)} for i in range(250)]
    out = signals.compute_asset_signals(bars)
    weights = [w for w in out["raw_weight"][200:] if w is not None]
    assert all(abs(w) <= config.MAX_ASSET_WEIGHT + 1e-9 for w in weights)
