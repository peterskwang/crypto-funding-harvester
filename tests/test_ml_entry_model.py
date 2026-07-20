import numpy as np
import pytest

from ml_entry_strategy import config
from ml_entry_strategy.strategy import model


def test_fit_standardizer_zero_mean_unit_std():
    rng = np.random.default_rng(0)
    X = rng.normal(loc=5.0, scale=3.0, size=(200, 4))
    mean, std = model.fit_standardizer(X)
    X_std = model.apply_standardizer(X, mean, std)
    assert np.allclose(X_std.mean(axis=0), 0.0, atol=1e-8)
    assert np.allclose(X_std.std(axis=0), 1.0, atol=1e-8)


def test_fit_standardizer_handles_zero_variance_column():
    X = np.column_stack([np.full(50, 7.0), np.arange(50, dtype=float)])
    mean, std = model.fit_standardizer(X)
    assert std[0] == 1.0  # guarded against divide-by-zero, not left at 0
    X_std = model.apply_standardizer(X, mean, std)
    assert np.allclose(X_std[:, 0], 0.0)


def test_train_logistic_recovers_a_clearly_separable_pattern():
    rng = np.random.default_rng(42)
    n = 400
    x = rng.normal(size=(n, 1))
    y = (x[:, 0] > 0).astype(float)
    w, b = model.train_logistic(x, y, lr=0.5, epochs=1000, l2=0.0)
    p = model.predict_proba(x, w, b)
    preds = (p >= 0.5).astype(float)
    accuracy = (preds == y).mean()
    assert accuracy > 0.95
    assert w[0] > 0  # positive x should predict label 1


def test_predict_proba_bounded_between_zero_and_one():
    X = np.array([[100.0], [-100.0], [0.0]])
    w = np.array([1.0])
    p = model.predict_proba(X, w, 0.0)
    assert np.all(p >= 0.0) and np.all(p <= 1.0)
    assert p[0] > 0.99
    assert p[1] < 0.01
    assert p[2] == pytest.approx(0.5)


def test_brier_score_perfect_predictions_is_zero():
    y = np.array([1.0, 0.0, 1.0, 0.0])
    p = np.array([1.0, 0.0, 1.0, 0.0])
    assert model.brier_score(y, p) == pytest.approx(0.0)


def test_brier_score_worst_case_predictions_is_one():
    y = np.array([1.0, 0.0])
    p = np.array([0.0, 1.0])
    assert model.brier_score(y, p) == pytest.approx(1.0)


def test_auc_score_perfect_ranking_is_one():
    y = np.array([0.0, 0.0, 1.0, 1.0])
    p = np.array([0.1, 0.2, 0.8, 0.9])
    assert model.auc_score(y, p) == pytest.approx(1.0)


def test_auc_score_inverted_ranking_is_zero():
    y = np.array([0.0, 0.0, 1.0, 1.0])
    p = np.array([0.9, 0.8, 0.2, 0.1])
    assert model.auc_score(y, p) == pytest.approx(0.0)


def test_auc_score_nan_when_single_class():
    y = np.array([1.0, 1.0, 1.0])
    p = np.array([0.2, 0.5, 0.9])
    assert np.isnan(model.auc_score(y, p))


def test_calibration_table_matches_hand_computed_buckets():
    # p=0.1,0.15 -> [0,0.3); p=0.55 -> [0.3,0.6); p=0.65,0.9 -> [0.6,1.0]
    y = np.array([1.0, 0.0, 1.0, 1.0, 0.0])
    p = np.array([0.1, 0.15, 0.55, 0.65, 0.9])
    edges = [0.0, 0.3, 0.6, 1.0]
    table = model.calibration_table(y, p, edges)
    assert table[0]["n"] == 2
    assert table[0]["actual_rate"] == pytest.approx(0.5)  # labels 1,0
    assert table[1]["n"] == 1
    assert table[1]["actual_rate"] == pytest.approx(1.0)  # label 1
    assert table[2]["n"] == 2
    assert table[2]["actual_rate"] == pytest.approx(0.5)  # labels 1,0


def test_calibration_table_empty_bucket_reports_zero_n():
    y = np.array([1.0, 0.0])
    p = np.array([0.05, 0.1])
    edges = [0.0, 0.2, 0.5, 1.0]
    table = model.calibration_table(y, p, edges)
    assert table[1]["n"] == 0
    assert table[1]["predicted_mean"] is None
    assert table[1]["actual_rate"] is None


def test_split_by_date_separates_correctly():
    bars = [
        {"date": "2026-01-01 00:00:00"},
        {"date": "2026-01-05 00:00:00"},
        {"date": "2026-01-10 00:00:00"},
        {"date": "2026-01-15 00:00:00"},
    ]
    idxs = [0, 1, 2, 3]
    is_mask, oos_mask = model.split_by_date(bars, idxs, "2026-01-10")
    assert list(is_mask) == [True, True, False, False]
    assert list(oos_mask) == [False, False, True, True]


def test_build_dataset_excludes_unresolved_and_warmup_rows():
    # needs real variation in price/volume -- a fully constant series makes
    # volume_zscore's baseline std 0, which correctly stays None forever
    # and would make every row get filtered out for the wrong reason.
    bars = []
    for i in range(150):
        c = 100.0 + 0.01 * (i % 7) + 0.001 * i
        v = 1_000_000 + 10_000 * (i % 5)
        bars.append({"open": c - 0.05, "high": c + 0.1, "low": c - 0.1, "close": c, "volume": v})
    X, y, idxs = model.build_dataset(bars, "long")
    assert len(X) == len(y) == len(idxs)
    assert len(idxs) > 0
    # every returned index must have a full, non-None feature row and a resolved label
    assert max(idxs) < len(bars) - config.MAX_HOLD_BARS
    assert X.shape[1] == len(config.FEATURE_NAMES)
