import math

import pytest

from fx_statarb_strategy.strategy import pairs


def test_ols_beta_perfect_linear_relationship():
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [2.0, 4.0, 6.0, 8.0, 10.0]  # y = 2x exactly
    assert pairs.ols_beta(y, x) == pytest.approx(2.0)


def test_ols_beta_zero_variance_x_returns_zero():
    x = [5.0, 5.0, 5.0]
    y = [1.0, 2.0, 3.0]
    assert pairs.ols_beta(y, x) == 0.0


def test_log_prices():
    out = pairs.log_prices([1.0, math.e, math.e ** 2])
    assert out == pytest.approx([0.0, 1.0, 2.0])


def test_static_hedge_ratio_matches_ols_beta_on_log_prices():
    eur = [1.10, 1.12, 1.11, 1.13]
    gbp = [1.30, 1.32, 1.31, 1.33]
    expected = pairs.ols_beta(pairs.log_prices(eur), pairs.log_prices(gbp))
    assert pairs.static_hedge_ratio(eur, gbp) == pytest.approx(expected)


def test_spread_series_static_beta():
    eur = [1.10, 1.12]
    gbp = [1.30, 1.32]
    spread = pairs.spread_series(eur, gbp, beta=2.0)
    expected = [math.log(1.10) - 2.0 * math.log(1.30), math.log(1.12) - 2.0 * math.log(1.32)]
    assert spread == pytest.approx(expected)


def test_spread_series_rolling_beta_with_none_propagates_none():
    eur = [1.10, 1.12, 1.11]
    gbp = [1.30, 1.32, 1.31]
    spread = pairs.spread_series(eur, gbp, beta=[None, 1.5, 1.5])
    assert spread[0] is None
    assert spread[1] is not None


def test_rolling_zscore_flat_series_is_none_zero_variance():
    series = [1.0] * 20
    z = pairs.rolling_zscore(series, lookback=10)
    # zero variance window -> None, not a divide-by-zero crash
    assert all(v is None for v in z[10:])


def test_rolling_zscore_normal_case():
    # window of [1,2,3,4,5,6,7,8,9,10], next value 20 -> clearly high z
    series = list(range(1, 11)) + [20]
    z = pairs.rolling_zscore(series, lookback=10)
    assert z[10] is not None
    assert z[10] > 2.0


def test_variance_ratio_mean_reverting_series_below_one():
    # An alternating series (strong negative autocorrelation) is the most
    # mean-reverting case possible -- k-bar returns should be much smaller
    # than k times the 1-bar variance.
    series = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0] * 5
    vr = pairs.variance_ratio(series, k=2)
    assert vr is not None
    assert vr < 1.0


def test_variance_ratio_trending_series_above_one():
    # A deterministic linear trend is the WRONG way to construct a
    # "trending" fixture here: VR measures autocorrelation in the random
    # component, and a pure drift contributes zero variance either way
    # (caught during development -- linear trend + i.i.d.-ish noise gave
    # VR < 1, not > 1, since the noise itself wasn't autocorrelated).
    # Momentum (VR > 1) requires genuine positive autocorrelation in the
    # increments, constructed here via a simple AR(1)-style persistence.
    incr = [1.0]
    for i in range(1, 60):
        shock = 0.05 * ((i * 37) % 7 - 3)
        incr.append(0.8 * incr[-1] + shock)
    series = [0.0]
    for d in incr:
        series.append(series[-1] + d)

    vr = pairs.variance_ratio(series, k=4)
    assert vr is not None
    assert vr > 1.0


def test_variance_ratio_insufficient_data_returns_none():
    assert pairs.variance_ratio([1.0, 2.0, 3.0], k=8) is None


def test_variance_ratio_zero_variance_returns_none():
    assert pairs.variance_ratio([5.0] * 40, k=4) is None


def test_rolling_hedge_ratios_ewma_is_smoother_than_step_update():
    # Construct closes where the "true" relationship shifts partway through
    # so raw per-window OLS estimates jump; EWMA should smooth that jump
    # while a step-update should show it immediately at the update boundary.
    import random
    random.seed(0)
    n = 200
    gbp = [1.30 + 0.0001 * i for i in range(n)]
    eur = [1.10 + 0.5 * (g - 1.30) for g in gbp[:100]] + [1.10 + 1.5 * (g - gbp[100]) for g in gbp[100:]]

    ewma = pairs.rolling_hedge_ratios(eur, gbp, lookback=50, ewma_alpha=0.05)
    step = pairs.rolling_hedge_ratios(eur, gbp, lookback=50, update_every=20)

    def _max_step_change(series):
        vals = [v for v in series if v is not None]
        return max(abs(vals[i] - vals[i - 1]) for i in range(1, len(vals)))

    assert _max_step_change(ewma) < _max_step_change(step)
