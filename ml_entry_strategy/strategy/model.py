"""Logistic regression training and calibration validation.

The deliverable this whole project is testing: when the model says a bar
has a 77% chance of being a good entry, does that number actually mean
anything? build_dataset() and fit_standardizer() are only ever touched
with in-sample rows; the out-of-sample rows are standardized with the
in-sample mean/std and never used to refit anything -- they're scored
once, and the calibration table compares predicted probability to actual
empirical outcome.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from ml_entry_strategy import config
from ml_entry_strategy.strategy import features, labels


def build_dataset(bars: List[dict], direction: str) -> Tuple[np.ndarray, np.ndarray, List[int]]:
    """Returns (X, y, bar_indices) for every bar with a complete feature
    row AND a resolved label. bar_indices lets callers map rows back to
    bars[t] (e.g. to split by date, or inspect a specific row)."""
    feats = features.compute_all_features(bars)
    lbls = labels.label_bars(bars, direction)

    X_rows, y_rows, idxs = [], [], []
    for t in range(len(bars)):
        if lbls[t] is None:
            continue
        row = [feats[name][t] for name in config.FEATURE_NAMES]
        if any(v is None for v in row):
            continue
        X_rows.append(row)
        y_rows.append(lbls[t]["label"])
        idxs.append(t)
    return np.array(X_rows, dtype=float), np.array(y_rows, dtype=float), idxs


def split_by_date(bars: List[dict], idxs: List[int], split_date: str) -> Tuple[np.ndarray, np.ndarray]:
    """Returns a boolean mask (is_in_sample) for the rows in idxs, based
    on each row's bar date vs config.IN_SAMPLE_END_DATE."""
    is_mask = np.array([bars[t]["date"][:10] < split_date for t in idxs])
    return is_mask, ~is_mask


def fit_standardizer(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0
    return mean, std


def apply_standardizer(X: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return (X - mean) / std


def train_logistic(X: np.ndarray, y: np.ndarray, lr: float = None, epochs: int = None, l2: float = None) -> Tuple[np.ndarray, float]:
    """Plain batch gradient descent -- deliberately simple and
    dependency-light, matching the from-scratch style of the rest of this
    session's strategy code. L2-regularized cross-entropy loss."""
    lr = lr if lr is not None else config.LOGISTIC_LR
    epochs = epochs if epochs is not None else config.LOGISTIC_EPOCHS
    l2 = l2 if l2 is not None else config.LOGISTIC_L2

    n, d = X.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(epochs):
        z = X @ w + b
        p = 1.0 / (1.0 + np.exp(-z))
        grad_w = X.T @ (p - y) / n + l2 * w
        grad_b = float(np.sum(p - y) / n)
        w -= lr * grad_w
        b -= lr * grad_b
    return w, b


def predict_proba(X: np.ndarray, w: np.ndarray, b: float) -> np.ndarray:
    z = X @ w + b
    return 1.0 / (1.0 + np.exp(-z))


def brier_score(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def auc_score(y: np.ndarray, p: np.ndarray) -> float:
    """Rank-based AUC (Mann-Whitney U). Ties aren't rank-averaged, which
    is a minor approximation acceptable for this diagnostic use."""
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(p)
    ranks = np.empty(len(p))
    ranks[order] = np.arange(1, len(p) + 1)
    sum_ranks_pos = ranks[y == 1].sum()
    return float((sum_ranks_pos - n1 * (n1 + 1) / 2) / (n1 * n0))


def calibration_table(y: np.ndarray, p: np.ndarray, edges: List[float] = None) -> List[dict]:
    """The core validation: for each predicted-probability bucket, does
    the ACTUAL empirical hit rate in that bucket match what the model
    claimed? This is what tells us whether a stated "77%" is trustworthy."""
    edges = edges or config.CALIBRATION_BUCKET_EDGES
    rows = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        is_last = i == len(edges) - 2
        mask = (p >= lo) & (p <= hi) if is_last else (p >= lo) & (p < hi)
        n = int(mask.sum())
        if n == 0:
            rows.append({"bucket": (lo, hi), "n": 0, "predicted_mean": None, "actual_rate": None})
            continue
        rows.append({
            "bucket": (lo, hi),
            "n": n,
            "predicted_mean": float(p[mask].mean()),
            "actual_rate": float(y[mask].mean()),
        })
    return rows
