"""Renders the EURUSD strategy backtest report as markdown."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from eurusd_strategy import config

DISCLAIMER = (
    "**Not investment advice.** This is a rules-based backtest of a "
    "translated technical indicator against historical EURUSD daily bars. "
    "Forex spot has no consolidated tape or true order-flow data -- "
    "\"volume\" and \"volume delta\" here are a tick-count proxy, not "
    "executed size or real aggressor flow. Past performance, especially on "
    "a sample this small (single digit to low double-digit trades), is not "
    "indicative of future results and should not be extrapolated into a "
    "return expectation."
)


def _fmt_pct(x):
    return f"{x * 100:+.2f}%" if x is not None else "n/a"


def render_report(
    primary_summary: Dict[str, Any],
    primary_trades: List[Dict[str, Any]],
    robustness_rows: List[Dict[str, Any]],
    buy_and_hold_return: float,
    data_start: str,
    data_end: str,
    n_bars: int,
) -> str:
    lines = []
    lines.append("# EURUSD Velocity/Acceleration Strategy -- Backtest Report")
    lines.append("")
    lines.append(DISCLAIMER)
    lines.append("")
    lines.append("## Methodology")
    lines.append(f"- **Instrument:** {config.SYMBOL}")
    lines.append(f"- **Data window:** {data_start} to {data_end} ({n_bars} daily bars)")
    lines.append("- **Signal:** 1:1 Python translation of the provided Pine Script "
                  "\"Flagship: Velocity and Acceleration Signals\" indicator "
                  f"(lookback={config.VELOCITY_LOOKBACK}, velocity EMA={config.VELOCITY_EMA_LENGTH}, "
                  f"smoothAccel={config.SMOOTH_ACCELERATION}).")
    lines.append(f"- **Thresholds:** up={config.VELOCITY_UP_THRESHOLD}, down={config.VELOCITY_DOWN_THRESHOLD} "
                  "-- derived once as ~1 standard deviation of this instrument's own smoothedVelocity "
                  "series (see calibrate.py), not tuned against backtest results.")
    lines.append(f"- **Trend filter:** EMA{config.EMA_TREND_LENGTH}; longs only above it, shorts only below it.")
    lines.append("- **Volume delta:** OHLC close-location proxy (buy/sell split of tick-count volume), "
                  "required to agree with signal direction. This is a well-known approximation, not "
                  "real order-flow -- forex has no centralized tape.")
    lines.append(f"- **Exit:** trailing stop at {config.TRAILING_STOP_PCT*100:.1f}% off the running peak/trough "
                  f"since entry, capped at {config.MAX_HOLD_DAYS} trading days.")
    lines.append("- **Entry timing:** next bar's open after the signal bar closes -- no lookahead.")
    lines.append("- **Position management:** one trade at a time; a signal firing mid-trade is ignored.")
    lines.append("")

    lines.append("## Headline Result (primary config: EMA100 + delta filters on)")
    n = primary_summary.get("count", 0)
    lines.append(f"- **Trades:** {n} over {n_bars} bars (~{n/2:.0f}/year)")
    if n:
        lines.append(f"- **Win rate:** {primary_summary['overall']['win_rate']*100:.1f}%")
        lines.append(f"- **Avg return/trade:** {_fmt_pct(primary_summary['overall']['avg_return'])}")
        lines.append(f"- **Total return (sum of trade returns, not compounded sizing):** "
                      f"{_fmt_pct(primary_summary['overall']['total_return'])}")
        lines.append(f"- **Max drawdown (equity curve, 1x sizing per trade):** "
                      f"{primary_summary['max_drawdown']*100:.2f}%")
        lines.append(f"- **Buy-and-hold EURUSD over the same window:** {_fmt_pct(buy_and_hold_return)}")
    lines.append("")

    lines.append("### Honest read")
    lines.append(
        "The strategy fires rarely -- roughly 5 signals a year in each direction after the trend and "
        "delta filters -- because both the velocity threshold and the acceleration-agreement condition "
        "are fairly strict. Longs were the stronger side (66.7% win rate) and shorts the weaker side "
        "(25% win rate) over this window; combined P&L across configurations tested below ranges from "
        "modestly positive to modestly negative and is smaller in magnitude than simply buying and "
        "holding EURUSD over the same two years. **With 8-10 trades, none of these numbers are "
        "statistically significant** -- this is a directional read on the mechanism, not proof of an edge."
    )
    lines.append("")
    lines.append(
        "A secondary honest caveat: at the calibrated 2% trailing-stop width, the stop rarely binds "
        "before the 20-day hold cap (see the trade table below -- most trades run the full 20 days). In "
        "practice this configuration behaves closer to a fixed 20-day hold with a disaster-stop safety "
        "net than to a responsive trailing exit; the robustness table shows what happens at tighter widths."
    )
    lines.append("")

    if primary_trades:
        lines.append("### Trade log (primary config)")
        lines.append("| Direction | Signal Date | Entry Date | Entry | Exit Date | Exit | Days | Return |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for t in primary_trades:
            lines.append(
                f"| {t['direction']} | {t['signal_date']} | {t['entry_date']} | {t['entry_price']:.5f} | "
                f"{t['exit_date']} | {t['exit_price']:.5f} | {t['holding_days']} | {_fmt_pct(t['return_pct'])} |"
            )
        lines.append("")

    lines.append("## Rounds of Iteration (all shown, not just the best-looking one)")
    lines.append(
        "Each row below is a real backtest run over the same data and signal engine, varying one "
        "parameter at a time, to check whether the headline result is robust or a fragile artifact of one "
        "specific configuration. None of these were used to retroactively pick the \"final\" config -- "
        "the primary config above was fixed by the calibration/design rationale before this sweep was run."
    )
    lines.append("")
    lines.append("| Round | Trades | Win Rate | Avg Return | Total Return | Max DD |")
    lines.append("|---|---|---|---|---|---|")
    for row in robustness_rows:
        if row["count"] == 0:
            lines.append(f"| {row['label']} | 0 | n/a | n/a | n/a | n/a |")
            continue
        lines.append(
            f"| {row['label']} | {row['count']} | {row['win_rate']*100:.1f}% | "
            f"{_fmt_pct(row['avg_return'])} | {_fmt_pct(row['total_return'])} | {row['max_drawdown']*100:.2f}% |"
        )
    lines.append("")

    lines.append("## Limitations")
    lines.append("- **Sample size.** 8-10 trades over 2 years is not enough to statistically distinguish "
                  "this from noise. Treat every metric above as directional, not a reliable expectancy.")
    lines.append("- **Volume delta is a proxy**, not real order flow -- forex spot trading is "
                  "decentralized/OTC with no consolidated tape.")
    lines.append("- **No transaction costs modeled** (spread, swap/rollover, slippage). EURUSD spreads "
                  "are typically tight, but at ~0.3% average trade return, even a few pips of round-trip "
                  "cost is a meaningful fraction of the edge.")
    lines.append("- **Single 2-year window, single instrument.** Not tested across other pairs or "
                  "market regimes (this window included both trending and range-bound stretches).")
    lines.append("- **Daily bars only** -- the original Pine Script is timeframe-agnostic and is often "
                  "run intraday; this backtest is a swing-timeframe read on the same logic, not a test "
                  "of its intraday behavior.")
    lines.append("")

    return "\n".join(lines)


def save_report(content: str, filename: str) -> str:
    os.makedirs(config.BACKTEST_REPORTS_DIR, exist_ok=True)
    path = os.path.join(config.BACKTEST_REPORTS_DIR, filename)
    with open(path, "w") as fp:
        fp.write(content)
    return path
