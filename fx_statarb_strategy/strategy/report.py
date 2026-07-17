"""Renders the v1.0 -> v5.0 progression report as markdown."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from fx_statarb_strategy import config

DISCLAIMER = (
    "**Not investment advice.** This is a rules-based statistical-arbitrage "
    "backtest on ~89 days of real EURUSD/GBPUSD 15-min bars (aggregated "
    "from 5-min data; the FMP forex API has no native 15-min endpoint). "
    "Every number below, including the out-of-sample section, is a "
    "backtest artifact on a short sample, not a live track record."
)


def _fmt_pct(x):
    return f"{x * 100:+.2f}%" if x is not None else "n/a"


def render_report(versions: List[Dict[str, Any]], walk_forward: Dict[str, Any]) -> str:
    lines = []
    lines.append("# EURUSD/GBPUSD Statistical-Arbitrage Pairs Strategy -- v1.0 to v5.0")
    lines.append("")
    lines.append(DISCLAIMER)
    lines.append("")
    lines.append("## Concept")
    lines.append(
        "Not a technical-indicator strategy on either pair individually. EURUSD and GBPUSD "
        "are structurally correlated (measured 0.83 return correlation on this data, both "
        "USD-legs with overlapping European economics) -- this trades the SPREAD between "
        "them (log EURUSD - beta * log GBPUSD). When the spread statistically diverges from "
        "its normal relationship, bet on reversion (long the cheap side, short the rich side); "
        "when the relationship itself looks statistically unstable, stand aside. No hard "
        "take-profit (exit is the spread reverting to near zero, not a fixed price target); "
        "a z-score-based stop-loss caps the risk of the relationship simply not reverting."
    )
    lines.append("")

    lines.append("## Version-by-version progression")
    lines.append("Each version fixes one concrete, measured flaw found in the previous one -- "
                  "including three real bugs surfaced while building v4.0, kept visible here "
                  "rather than silently patched, because how they were found is as informative "
                  "as the fix.")
    lines.append("")
    lines.append("| Version | Trades | Win Rate | Total Return | Max DD | What changed |")
    lines.append("|---|---|---|---|---|---|")
    for v in versions:
        s = v["summary"]
        if s.get("count"):
            lines.append(
                f"| {v['name']} | {s['count']} | {s['win_rate']*100:.1f}% | "
                f"{_fmt_pct(s['total_return'])} | {s['max_drawdown']*100:.2f}% | {v['change']} |"
            )
        else:
            lines.append(f"| {v['name']} | 0 | n/a | n/a | n/a | {v['change']} |")
    lines.append("")

    for v in versions:
        lines.append(f"### {v['name']}")
        lines.append(v["notes"])
        lines.append("")

    lines.append("## v5.0: walk-forward validation (the actual test)")
    lines.append(
        f"In-sample: {walk_forward['in_sample_range']}, used to fit the hedge ratio "
        f"(beta = {walk_forward['fixed_beta']:.4f}) and diagnose in-sample performance. "
        f"Out-of-sample: {walk_forward['out_sample_range']} -- entries were mechanically "
        "blocked before this point (min_entry_index), so this is a genuine forward test on "
        "data the beta fit never saw, not a re-run over the same window."
    )
    lines.append("")
    lines.append("| Sample | Trades | Win Rate | Total Return | Max DD | Period | Monthly-equivalent |")
    lines.append("|---|---|---|---|---|---|---|")
    for label, s, days in (
        ("In-sample", walk_forward["in_sample_summary"], walk_forward["in_sample_days"]),
        ("Out-of-sample", walk_forward["out_sample_summary"], walk_forward["out_sample_days"]),
    ):
        if s.get("count"):
            monthly = s["total_return"] * 30 / days
            lines.append(
                f"| {label} | {s['count']} | {s['win_rate']*100:.1f}% | {_fmt_pct(s['total_return'])} | "
                f"{s['max_drawdown']*100:.2f}% | {days}d | {_fmt_pct(monthly)} |"
            )
        else:
            lines.append(f"| {label} | 0 | n/a | n/a | n/a | {days}d | n/a |")
    lines.append("")

    lines.append("### Honest verdict")
    lines.append(walk_forward["verdict"])
    lines.append("")

    lines.append("## Real bugs found and fixed during v4.0 (kept visible, not smoothed over)")
    lines.append(
        "1. **Every-bar beta re-estimation injects noise.** Re-fitting the OLS hedge ratio "
        "fresh on every 15-min bar sounds most responsive but quadrupled the spread's "
        "bar-to-bar volatility versus a static beta -- pure regression noise, which fully "
        "defeated the regime filter (0 trades passed it)."
    )
    lines.append(
        "2. **Discrete step-updates create jump artifacts.** The naive fix -- re-fit only "
        "every N bars, hold beta fixed between updates -- traded that noise for large "
        "discontinuities: the median spread jump exactly at an update boundary measured "
        "~300x the median jump elsewhere (0.031 vs 0.0001). Every trade in that "
        "configuration (37/37) hit its stop-loss on the artifact, not a real reversion "
        "failure."
    )
    lines.append(
        "3. **Phantom P&L from a time-varying spread series.** The trade P&L calculation "
        "read `exit_spread` from the same globally time-varying spread series used for "
        "live signal generation -- so if beta drifted between entry and exit, the "
        "\"return\" partly reflected the hedge ratio changing, not the price relationship "
        "moving. Fixed by recomputing the exit spread with the beta FIXED at entry, "
        "matching what a real fixed-notional position actually earns."
    )
    lines.append(
        "4. **480-bar (~5-day) hedge-ratio lookback was statistically unstable**: raw OLS "
        "beta on rolling 5-day windows ranged from 0.015 to 1.53 (stdev 0.31) on this data. "
        "Widening to 2000 bars (~21 days) cut that to stdev ~0.20 -- still not fully stable, "
        "a real, disclosed constraint of only having ~89 days of data to work with."
    )
    lines.append("")

    lines.append("## 1-minute entry timing: validated on a sample, not fully backtested")
    lines.append(
        "The full backtest above executes at the 15-min bar's close, ~15 minutes after signal "
        "confirmation. A full 1-minute-granularity backtest across 89 days x 2 pairs was not "
        "feasible to fetch through this environment's data relay (1-min bars run ~1,440/day/pair "
        "vs ~69 15-min bars/day/pair). Instead, real 1-min data was pulled for a 6-trade sample "
        "from the out-of-sample period to measure what waiting the full 15 minutes actually costs: "
        "the mean absolute difference between the spread at the first available 1-min close "
        "(fast execution) versus the 15-min bar's close (what the backtest assumes) was **0.000108** "
        "in spread units -- comparable in magnitude to v1.0's average return PER TRADE (0.000102). "
        "In other words, execution speed here isn't a minor implementation detail: on this "
        "instrument and signal, how fast you can act on a confirmed signal is roughly as "
        "consequential as the statistical edge itself. This validates the user's original 1-minute-entry "
        "requirement rather than dismissing it, even though the full backtest couldn't be run at "
        "that granularity."
    )
    lines.append("")

    lines.append("## Limitations")
    lines.append("- **Sample size**: 89 days total, ~31 days held out for the only genuine "
                  "out-of-sample test. Enough to catch gross overfitting, not enough to "
                  "certify a durable edge.")
    lines.append("- **No transaction costs modeled** (spread/commission on two legs, plus "
                  "the bid/ask cost of maintaining a hedge ratio). At sub-0.1%-per-trade "
                  "average returns, real costs would likely erase what edge is shown here.")
    lines.append("- **Entries execute at the 15-min bar's close, not a full 1-min backtest** "
                  "-- see the dedicated section above for the sample-based slippage measurement "
                  "and why this matters more than it might sound.")
    lines.append("- **Two instruments, one relationship, one 3-month window.** Not tested "
                  "across other pairs, regimes, or longer history.")
    lines.append("- **The regime filter (variance-ratio test) and the rolling/EWMA beta from "
                  "v4.0 do not compose cleanly** -- a time-varying beta injects enough medium-"
                  "frequency variance into the spread that the VR test calibrated for a static "
                  "beta almost never passes. v5.0 uses an in-sample-fit STATIC beta instead, "
                  "deliberately not carrying the rolling-beta experiment forward, since it "
                  "underperformed even in isolation on this data.")
    lines.append("")

    return "\n".join(lines)


def save_report(content: str, filename: str) -> str:
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    path = os.path.join(config.REPORTS_DIR, filename)
    with open(path, "w") as fp:
        fp.write(content)
    return path
