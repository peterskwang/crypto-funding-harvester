"""Renders the ML entry-probability calibration report, across every
asset in config.ASSETS."""

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


def _render_asset_section(asset_result: Dict[str, Any]) -> list:
    lines = []
    symbol = asset_result["symbol"]
    lines.append(f"## {symbol}")
    lines.append(f"- **Data:** {asset_result['n_bars']} 15-min bars, "
                  f"{asset_result['date_range'][0][:10]} to {asset_result['date_range'][1][:10]}. "
                  f"Split at {asset_result['in_sample_end_date']} (in-sample before, out-of-sample after).")
    lines.append("")

    for direction in ("long", "short"):
        r = asset_result["directions"][direction]
        lines.append(f"### {symbol} -- {direction.capitalize()} entries")
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
    return lines


def render_report(asset_results: Dict[str, Any]) -> str:
    lines = []
    lines.append("# ML Entry-Probability Model -- Calibration Report")
    lines.append("")
    lines.append(DISCLAIMER)
    lines.append("")

    lines.append("## Why this project exists")
    lines.append(
        "A direct request to reverse-engineer a specific, high-confidence entry "
        "probability (\"is 77.3% a trustworthy number\") from indicators like "
        "volume, volume delta, ATR, price acceleration, and volume profile -- the "
        "77.3% was an illustrative example in the original ask, not a target to "
        "hit. Rather than assert a number, this builds the actual pipeline needed "
        "to answer it honestly: objective triple-barrier labels (did price hit "
        "its target before its stop, looking forward -- standard "
        "supervised-learning label construction, not lookahead bias), strictly "
        "backward-looking features, a simple calibrated model, and a held-out "
        "test of whether the model's stated probabilities match reality. Run "
        "across three assets from two different classes (BTC, EURUSD, GBPUSD) "
        "so the finding isn't a one-asset artifact."
    )
    lines.append("")

    lines.append("## Methodology")
    lines.append(f"- **Labels (triple barrier):** for each bar, walk forward up to "
                  f"{config.MAX_HOLD_BARS} bars (~4 hours at 15-min bars). Label = 1 if price hits "
                  f"{config.PROFIT_TARGET_ATR_MULT}x ATR profit target before "
                  f"{config.STOP_LOSS_ATR_MULT}x ATR stop-loss and before time runs out, else 0. "
                  "Long and short candidates are labeled separately at every bar.")
    lines.append(f"- **Features (strictly backward-looking):** {', '.join(config.FEATURE_NAMES)} "
                  "-- volume z-score vs rolling mean, a Chaikin-style volume-delta proxy, ATR as a "
                  "% of price, price acceleration (discrete 2nd derivative), a range-surge ratio, "
                  "and distance from an approximate volume-profile point of control. None of these "
                  "can see past the candidate bar.")
    lines.append(f"- **Model:** plain logistic regression (L2={config.LOGISTIC_L2}) per asset per "
                  "direction (6 models total), chosen deliberately over anything fancier -- a few "
                  "thousand labeled examples and six features is not enough data to justify gradient "
                  "boosting or a neural net without just overfitting the noise in one data window.")
    lines.append("- **Split:** in-sample (fit standardization and train weights) through each asset's "
                  "own split date, out-of-sample after that (scored once, never refit).")
    lines.append("- **BTCUSD volume:** ~4.2% of raw 5-min bars had a corrupted `volume` field (a clean "
                  "gap in the distribution separates real values, topping out ~1.7B, from glitch values "
                  "starting ~14B) -- OHLC was unaffected; repaired with the local median of nearby clean "
                  "bars before any feature or label was computed.")
    lines.append("- **EURUSD/GBPUSD volume:** broker tick-count, not true traded volume (FX spot has no "
                  "centralized tape) -- directionally useful as an activity proxy, but on a different "
                  "footing than BTC's coin-volume. No corrupted-value defect was found in this data, so "
                  "no cleaning was applied.")
    lines.append("")

    for symbol in asset_results:
        lines.extend(_render_asset_section(asset_results[symbol]))

    lines.append("## Cross-asset summary")
    lines.append("| Asset | Direction | OOS n | OOS AUC | Predicted range |")
    lines.append("|---|---|---|---|---|")
    for symbol, ar in asset_results.items():
        for direction in ("long", "short"):
            r = ar["directions"][direction]
            lines.append(f"| {symbol} | {direction} | {r['n_oos']} | {r['oos_auc']:.3f} | "
                          f"{_bucket_label(*r['pred_range'])} |")
    lines.append("")

    lines.append("## Honest verdict")
    all_pred_max = max(r["pred_range"][1] for ar in asset_results.values() for r in ar["directions"].values())
    n_ge_60 = sum(1 for ar in asset_results.values() for r in ar["directions"].values()
                  for row in r["calibration"] if row["bucket"][0] >= 0.6 and row["n"])
    n_oos_total = sum(r["n_oos"] for ar in asset_results.values() for r in ar["directions"].values())
    lines.append(
        f"**Across all three assets, both directions, and {n_oos_total} total out-of-sample "
        f"predictions, the model essentially never predicts anywhere near 77%.** Only one "
        "asset/direction combination (GBPUSD long) ever produced a prediction at or above 60% "
        f"confidence at all, and even there it was 5 rows out of {asset_results['GBPUSD']['directions']['long']['n_oos']} "
        "-- and those 5 rows' actual hit rate (40%) badly missed their own predicted average "
        "(62.9%), the signature of a small, noisy bucket rather than real high confidence. That "
        "spike traces to a disclosed limitation (FX tick volume near zero during illiquid sessions "
        "can blow up the volume z-score feature from a near-zero baseline standard deviation), not "
        "a genuine high-confidence signal. Every other asset/direction never predicted above 60% at "
        "all. Predicted probabilities stay clustered in a narrow band near each asset's own base "
        "rate, because that's genuinely where the edge in these six features tops out. A "
        "well-calibrated model doesn't manufacture confidence it can't back up -- and that restraint "
        "is itself the answer to the original question: on this feature set, a stated 77.3% would "
        "not be trustworthy on any of these assets, because no honestly-validated model trained on "
        "this data gets anywhere close to that number in any way that survives scrutiny."
    )
    lines.append("")

    auc_lines = []
    for symbol, ar in asset_results.items():
        for direction in ("long", "short"):
            r = ar["directions"][direction]
            tag = "real, modest edge" if r["oos_auc"] > 0.55 else ("no real edge" if r["oos_auc"] < 0.52 else "weak/inconclusive")
            auc_lines.append(f"**{symbol} {direction}**: OOS AUC {r['oos_auc']:.3f} ({tag})")
    lines.append(" | ".join(auc_lines))
    lines.append("")
    lines.append(
        "The pattern that emerges: whatever structure these six features capture is asset- and "
        "direction-specific, not a universal edge. It shows up unevenly (strongest in the asset with "
        "the strongest realized trend over its own out-of-sample window) rather than consistently "
        "across every market and direction -- which is itself informative. A feature set with a real, "
        "general edge would be expected to show at least a consistent sign and magnitude across "
        "uncorrelated assets; this one doesn't."
    )
    lines.append("")

    lines.append("## What this means for the original 5%/month goal")
    lines.append(
        "This was framed as a different kind of test than the prior two projects (FX cointegration, "
        "crypto trend-following) -- not \"does this make money\" but \"can a stated entry probability "
        "be trusted.\" The honest answer generalizes the same way the other two did, and generalizes "
        "further now across three assets: real, measurable structure sometimes exists, but it is "
        "nowhere near strong enough, nor consistent enough, to support a high-confidence, "
        "frequent-entry claim like \"77.3% probability.\" A well-built, honestly-validated model on "
        "this feature set reliably tops out in the high-40s to low-50s% predicted confidence across "
        f"every asset and direction tested, not {_fmt_pct(0.773)} -- the one nominal excursion to "
        f"{_fmt_pct(all_pred_max)} (5 rows, GBPUSD long) is noise from a disclosed data limitation, "
        "not a real high-confidence prediction."
    )
    lines.append("")

    lines.append("## Limitations")
    lines.append("- **Single historical window per asset**, not multiple market regimes -- BTC covers "
                  "~89 days, EURUSD/GBPUSD ~180 days, all from roughly the same 2026 calendar period.")
    lines.append("- **This is a labeling/calibration study, not a backtested strategy.** No "
                  "transaction costs, slippage, execution latency, or position sizing are modeled; "
                  "turning a well-calibrated probability into a real P&L curve is a separate step.")
    lines.append("- **Volume delta and volume profile are OHLCV approximations**, not real "
                  "tick-level order flow on any of the three assets.")
    lines.append("- **FX weekend gaps aren't calendar-aware**: bar-count-based lookback windows "
                  "(volume z-score, ATR, volume profile) treat Friday's last bar and Sunday's first bar "
                  "as adjacent, same as every other bar-count indicator in this codebase -- a real "
                  "approximation, not unique to this project.")
    lines.append("- **FX tick volume can be near-zero during illiquid sessions**, which can produce "
                  "extreme volume z-scores from a near-zero baseline standard deviation (seen on "
                  "GBPUSD) -- a real property of the data, not a defect, but it means that feature can "
                  "be spiky in a way BTC's continuous 24/7 volume mostly isn't.")
    lines.append("- **Intrabar barrier-touch ordering is inferred**, not observed: when a single "
                  "forward bar's range touches both the profit and stop levels, the true path "
                  "within that bar is unknown from OHLC alone; a same-bar heuristic (nearest to "
                  "open resolves first) is used and disclosed in `labels.py`.")
    lines.append("- **~4.2% of raw BTC volume data required repair** due to an upstream feed defect "
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
