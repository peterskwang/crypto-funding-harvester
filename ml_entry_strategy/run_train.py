"""Entrypoint: trains the entry-probability model for long and short
candidates, validates calibration out-of-sample, and saves the report.
Usage: python -m ml_entry_strategy.run_train
"""

import datetime as dt

import numpy as np

from ml_entry_strategy import config
from ml_entry_strategy.strategy import bars, model, report


def _run_direction(all_bars, direction):
    X, y, idxs = model.build_dataset(all_bars, direction)
    is_mask, oos_mask = model.split_by_date(all_bars, idxs, config.IN_SAMPLE_END_DATE)
    X_is, y_is = X[is_mask], y[is_mask]
    X_oos, y_oos = X[oos_mask], y[oos_mask]

    mean, std = model.fit_standardizer(X_is)
    X_is_std = model.apply_standardizer(X_is, mean, std)
    X_oos_std = model.apply_standardizer(X_oos, mean, std)

    w, b = model.train_logistic(X_is_std, y_is)
    p_oos = model.predict_proba(X_oos_std, w, b)

    calibration = model.calibration_table(y_oos, p_oos)
    naive_brier = model.brier_score(y_oos, np.full_like(y_oos, y_is.mean()))
    pred_range = (float(p_oos.min()), float(p_oos.max()))

    return {
        "n_is": len(y_is),
        "n_oos": len(y_oos),
        "is_win_rate": float(y_is.mean()),
        "oos_win_rate": float(y_oos.mean()),
        "weights": dict(zip(config.FEATURE_NAMES, w.tolist())),
        "bias": float(b),
        "oos_auc": model.auc_score(y_oos, p_oos),
        "oos_brier": model.brier_score(y_oos, p_oos),
        "naive_brier": naive_brier,
        "pred_range": pred_range,
        "calibration": calibration,
    }


def main():
    all_bars = bars.load_15m()
    results = {direction: _run_direction(all_bars, direction) for direction in ("long", "short")}

    content = report.render_report(results)
    today = dt.date.today().isoformat()
    filename = f"{today}_ml_entry_calibration.md"
    path = report.save_report(content, filename)

    print(f"Saved report to {path}")
    for direction in ("long", "short"):
        r = results[direction]
        print(f"{direction:6s} OOS AUC={r['oos_auc']:.3f}  Brier={r['oos_brier']:.4f} "
              f"(naive={r['naive_brier']:.4f})  pred_range={r['pred_range'][0]*100:.1f}-{r['pred_range'][1]*100:.1f}%")


if __name__ == "__main__":
    main()
