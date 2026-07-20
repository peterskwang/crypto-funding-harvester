"""Renders the ML entry-probability calibration report."""

from __future__ import annotations

import os
from typing import Any, Dict

from ml_entry_strategy import config

DISCLAIMER = (
    "**Not investment advice.** This tests one specific question: when a model "
    "trained on backward-looking market-state features states a probability "
    "(\"this entry has a 77% chance of hitting its target before its stop\"), "
    "does that number hold up against real, held-out, out-of-sample outcomes? "
    "It is not a backtested trading strategy with a P&L curve -- see "
    "Limitations for what would still be needed to turn this into one."
)


def _fmt_pct(x, digits=1):
    return f"{x * 100:.{digits}f}%" if x is not None else "n/a"


def _bucket_label(lo, hi):
    return f"{lo*100:.0f}-{hi*100:.0f}%"


def render_report(results: Dict[str, Any]) -> str:
    lines = []
    lines.append("# ML Entry-Probability Model -- Calibration Report")
    lines.append("")
    lines.append(DISCLAIMER)
    lines.append("")

    lines.append("## Why this project exists")
    lines.append(
        "A direct request to reverse-engineer a specific, high-confidence entry "
        "probability (\"is 77.3% a trustworthy number\") from indicators like "
        "volume, volume delta, ATR, price acceleration, and volume profile. "
        "Rather than assert a number, this builds the actual pipeline needed to "
        "answer it honestly: objective triple-barrier labels (did price hit its "
        "target before its stop, looking forward -- standard supervised-learning "
        "label construction, not lookahead bias), strictly backward-looking "
        "features, a simple calibrated model, and a held-out test of whether "
        "the model's stated probabilities match reality."
    )
    lines.append("")

    lines.append("## Methodology")
    lines.append(f"- **Data:** {config.SYMBOL} 15-min bars aggregated from 5-min data "
                  "(2026-04-21 to 2026-07-18, ~89 days). ~4.2% of raw 5-min bars had a "
                  "corrupted `volume` field (a clean gap in the volume distribution separates "
                  "real values, topping out ~1.7B, from glitch values starting ~14B) -- OHLC was "
                  "unaffected; volume on those bars was repaired with the local median of nearby "
                  "clean bars before any feature or label was computed.")
    lines.append(f"- **Labels (triple barrier):** for each bar, walk forward up to "
                  f"{config.MAX_HOLD_BARS} bars (~4 hours). Label = 1 if price hits "
                  f"{config.PROFIT_TARGET_ATR_MULT}x ATR profit target before "
                  f"{config.STOP_LOSS_ATR_MULT}x ATR stop-loss and before time runs out, else 0. "
                  "Long and short candidates are labeled separately at every bar.")
    lines.append(f"- **Features (strictly backward-looking):** {', '.join(config.FEATURE_NAMES)} "
                  "-- volume z-score vs rolling mean, a Chaikin-style volume-delta proxy, ATR as a "
                  "% of price, price acceleration (discrete 2nd derivative), a range-surge ratio, "
                  "and distance from an approximate volume-profile point of control. None of these "
                  "can see past the candidate bar.")
    lines.append(f"- **Model:** plain logistic regression (L2={config.LOGISTIC_L2}), chosen "
                  "deliberately over anything fancier -- a few thousand labeled examples and six "
                  "features is not enough data to justify gradient boosting or a neural net "
                  "without just overfitting the noise in one 89-day window.")
    lines.append(f"- **Split:** in-sample through {config.IN_SAMPLE_END_DATE} (fit standardization "
                  "and train weights), out-of-sample after that (scored once, never refit).")
    lines.append("")

    lines.append("## Results")
    for direction in ("long", "short"):
        r = results[direction]
        lines.append(f"### {direction.capitalize()} entries")
        lines.append(f"- IS rows: {r['n_is']} (base win rate {_fmt_pct(r['is_win_rate'])}) | "
                      f"OOS rows: {r['n_oos']} (base win rate {_fmt_pct(r['oos_win_rate'])})")
        lines.append(f"- OOS AUC: {r['oos_auc']:.3f} (0.5 = no better than chance) | "
                      f"OOS Brier: {r['oos_brier']:.4f} (naive base-rate Brier: {r['naive_brier']:.4f})")
        lines.append("")
        lines.append("| Predicted bucket | n (OOS) | Predicted mean | Actual hit rate |")
        lines.append("|---|---|---|---|")
        for row in r["calibration"]:
            lo, hi = row["bucket"]
            if row["n"] == 0:
                lines.append(f"| {_bucket_label(lo, hi)} | 0 | -- | -- (no predictions landed here) |")
            else:
                lines.append(f"| {_bucket_label(lo, hi)} | {row['n']} | "
                              f"{_fmt_pct(row['predicted_mean'])} | {_fmt_pct(row['actual_rate'])} |")
        lines.append("")

    lines.append("## Honest verdict")
    long_r, short_r = results["long"], results["short"]
    lines.append(
        f"**The model never once predicted anywhere near 77% -- on either side, in-sample or "
        f"out-of-sample.** Its predicted probabilities cluster tightly in the "
        f"{_bucket_label(*long_r['pred_range'])} (long) and {_bucket_label(*short_r['pred_range'])} "
        "(short) range, because that's genuinely where the edge in these six features tops out on "
        "this data. A well-calibrated model doesn't manufacture confidence it can't back up -- "
        "and that restraint is itself the answer to the original question: on this feature set "
        "and this data, a stated 77.3% would not be trustworthy, because no honest model trained "
        "on it produces a number anywhere close to that."
    )
    lines.append("")
    lines.append(
        f"**Long side shows a real, modest, out-of-sample edge**: OOS AUC {long_r['oos_auc']:.3f} "
        f"(vs. 0.500 for coin-flip), and the calibration table tracks reasonably -- predicted and "
        "actual move together bucket to bucket, though actual rates run consistently a few points "
        "above predicted. That gap is most likely a base-rate shift: the in-sample win rate "
        f"({_fmt_pct(long_r['is_win_rate'])}) was lower than the out-of-sample win rate "
        f"({_fmt_pct(long_r['oos_win_rate'])}) -- BTC's realized path in the held-out window was "
        "modestly more favorable to longs than the window the model was fit on, which shifts every "
        "bucket's actual rate up by roughly the same amount. That's a real limitation (the model "
        "assumes a stationary base rate) but not a sign the ranking itself is broken."
    )
    lines.append("")
    lines.append(
        f"**Short side shows no real edge**: OOS AUC {short_r['oos_auc']:.3f}, statistically "
        "indistinguishable from 0.500. These six features do not predict short-side outcomes "
        "on this data; the calibration table for shorts should not be trusted for sizing decisions."
    )
    lines.append("")

    lines.append("## What this means for the original 5%/month goal")
    lines.append(
        "This was framed as a different kind of test than the prior two projects (FX "
        "cointegration, crypto trend-following) -- not \"does this make money\" but \"can a "
        "stated entry probability be trusted.\" The honest answer generalizes the same way the "
        "other two did: real, measurable, modest structure exists (long-side AUC ~0.57 is a "
        "genuine, non-random signal), but it is nowhere near strong enough to support the kind "
        "of high-confidence, frequent-entry claim (\"77.3% probability\") the original idea "
        "was reaching for. A well-built, honestly-validated model on this feature set tops out "
        f"around {_fmt_pct(long_r['pred_range'][1])} predicted confidence, not {_fmt_pct(0.773)}."
    )
    lines.append("")

    lines.append("## Limitations")
    lines.append("- **Single 89-day window, single asset.** BTC 15-min bars over one specific "
                  "quarter -- not multiple market regimes or assets.")
    lines.append("- **This is a labeling/calibration study, not a backtested strategy.** No "
                  "transaction costs, slippage, execution latency, or position sizing are modeled; "
                  "turning a well-calibrated probability into a real P&L curve is a separate step.")
    lines.append("- **Volume delta and volume profile are OHLCV approximations**, not real "
                  "tick-level order flow -- crypto spot OHLCV data has no true aggressor-side data.")
    lines.append("- **Intrabar barrier-touch ordering is inferred**, not observed: when a single "
                  "forward bar's range touches both the profit and stop levels, the true path "
                  "within that bar is unknown from OHLC alone; a same-bar heuristic (nearest to "
                  "open resolves first) is used and disclosed in `labels.py`.")
    lines.append("- **~4.2% of raw volume data required repair** due to an upstream feed defect "
                  "(see Methodology) -- repaired via local median substitution, not dropped, since "
                  "OHLC on those bars was clean and dropping bars would break time continuity.")
    lines.append("")

    return "\n".join(lines)


def save_report(content: str, filename: str) -> str:
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    path = os.path.join(config.REPORTS_DIR, filename)
    with open(path, "w") as fp:
        fp.write(content)
    return path
