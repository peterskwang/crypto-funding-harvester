import pytest

from ml_entry_strategy.strategy import features


def _bar(h, l, c, v, o=None):
    return {"open": o if o is not None else c, "high": h, "low": l, "close": c, "volume": v}


def test_true_range_first_bar_is_none():
    bars = [_bar(101, 99, 100, 10), _bar(103, 100, 102, 10)]
    tr = features.true_range(bars)
    assert tr[0] is None
    assert tr[1] == pytest.approx(3.0)  # high-low=3, high-prevclose=3, low-prevclose=0 -> max=3


def test_raw_atr_none_before_lookback_then_matches_mean_true_range():
    # constant true range of 2.0 each bar (h-l=2, no gaps) -> ATR should converge to 2.0
    # tr[0] is always None (no prior bar), so the window needs indices 1..lookback
    # to collect `lookback` non-None values -- first valid index is `lookback`, not lookback-1.
    bars = [_bar(101, 99, 100, 10) for _ in range(20)]
    atr = features.raw_atr(bars, lookback=5)
    assert atr[4] is None
    assert atr[5] is not None
    assert atr[10] == pytest.approx(2.0)


def test_atr_pct_is_raw_atr_divided_by_close():
    bars = [_bar(110, 90, 100, 10) for _ in range(20)]
    raw = features.raw_atr(bars, lookback=5)
    pct = features.atr_pct(bars, lookback=5)
    for r, p in zip(raw, pct):
        if r is None:
            assert p is None
        else:
            assert p == pytest.approx(r / 100.0)


def test_volume_zscore_none_before_lookback():
    # volume must vary (not constant) or the baseline std is 0 and the
    # function correctly declines to divide by zero, staying None forever.
    bars = [_bar(101, 99, 100, 1_000_000 + 1_000 * (i % 3)) for i in range(10)]
    vz = features.volume_zscore(bars, lookback=5)
    assert vz[4] is None
    assert vz[5] is not None


def test_volume_zscore_high_for_volume_spike():
    bars = [_bar(101, 99, 100, 1_000_000 + 1_000 * (i % 3)) for i in range(20)]
    bars.append(_bar(101, 99, 100, 50_000_000))  # spike bar
    vz = features.volume_zscore(bars, lookback=10)
    assert vz[-1] > 5  # should register as a large positive z-score


def test_volume_delta_norm_bounds_and_direction():
    # close near high -> positive (buy pressure); close near low -> negative
    buy_bar = _bar(h=110, l=100, c=109, v=1000)
    sell_bar = _bar(h=110, l=100, c=101, v=1000)
    flat_range_bar = _bar(h=100, l=100, c=100, v=1000)
    out = features.volume_delta_norm([buy_bar, sell_bar, flat_range_bar])
    assert -1.0 <= out[0] <= 1.0
    assert -1.0 <= out[1] <= 1.0
    assert out[0] > 0
    assert out[1] < 0
    assert out[2] == 0.0  # zero range -> defined as neutral, not divide-by-zero


def test_price_acceleration_positive_when_uptrend_speeds_up():
    # flat then accelerating up: roc_prior ~0, roc_recent > 0 -> positive accel
    closes = [100.0] * 8 + [101.0, 103.0, 106.0, 110.0]
    bars = [_bar(c + 1, c - 1, c, 10) for c in closes]
    accel = features.price_acceleration(bars, k=4)
    assert accel[-1] is not None
    assert accel[-1] > 0


def test_surge_ratio_flags_wide_range_bar():
    normal = [_bar(101, 99, 100, 10) for _ in range(20)]  # range=2 each
    wide = _bar(120, 80, 100, 10)  # range=40
    bars = normal + [wide]
    sr = features.surge_ratio(bars, lookback=10)
    assert sr[-1] == pytest.approx(20.0)  # 40 / 2


def test_dist_from_poc_pct_smaller_when_close_matches_heavy_volume_cluster():
    # window: a tight low-price band carries heavy volume, a separate
    # higher-price band carries light volume -- POC should sit near the
    # heavy cluster, so a close matching it should be nearer to POC than
    # a close matching the light cluster.
    window = [_bar(100.6, 99.4, 100.0, 1_000_000) for _ in range(40)]
    window += [_bar(110.6, 109.4, 110.0, 10_000) for _ in range(10)]
    candidate_near = _bar(100.6, 99.4, 100.0, 10)
    candidate_far = _bar(110.6, 109.4, 110.0, 10)

    dist_near = features.dist_from_poc_pct(window + [candidate_near], lookback=50, n_bins=20)[-1]
    dist_far = features.dist_from_poc_pct(window + [candidate_far], lookback=50, n_bins=20)[-1]

    assert dist_near is not None and dist_far is not None
    assert abs(dist_near) < abs(dist_far)


def test_compute_all_features_returns_same_length_series():
    bars = [_bar(101, 99, 100, 10) for _ in range(150)]
    feats = features.compute_all_features(bars)
    for name, series in feats.items():
        assert len(series) == len(bars), name
