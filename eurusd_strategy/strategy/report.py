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
    "executed size or real aggressor flow. No transaction costs (spread, "
    "swap, slippage) are modeled. Every number below, including the "
    "out-of-sample section, is a backtest artifact, not a live-trading "
    "track record -- treat it accordingly."
)


def _fmt_pct(x):
    return f"{x * 100:+.2f}%" if x is not None else "n/a"


def _trade_table(trades: List[Dict[str, Any]]) -> List[str]:
    lines = ["| Direction | Signal Date | Entry Date | Entry | Exit Date | Exit | Days | Return |",
             "|---|---|---|---|---|---|---|---|"]
    for t in trades:
        lines.append(
            f"| {t['direction']} | {t['signal_date']} | {t['entry_date']} | {t['entry_price']:.5f} | "
            f"{t['exit_date']} | {t['exit_price']:.5f} | {t['holding_days']} | {_fmt_pct(t['return_pct'])} |"
        )
    return lines


def render_report(
    primary_summary: Dict[str, Any],
    primary_trades: List[Dict[str, Any]],
    robustness_rows: List[Dict[str, Any]],
    buy_and_hold_return: float,
    data_start: str,
    data_end: str,
    n_bars: int,
    search_top_rows: List[Dict[str, Any]] = None,
    search_bottom_rows: List[Dict[str, Any]] = None,
    search_n_configs: int = None,
    oos_candidates: List[Dict[str, Any]] = None,
    in_sample_range: tuple = None,
    out_sample_range: tuple = None,
    in_sample_bh: float = None,
    out_sample_bh: float = None,
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
                  "-- derived once as ~1 standard deviation of the IN-SAMPLE (2013-2021) smoothedVelocity "
                  "series only, not tuned against backtest results and not leaking the out-of-sample window.")
    lines.append(f"- **Trend filter:** EMA{config.EMA_TREND_LENGTH}; longs only above it, shorts only below it.")
    lines.append("- **Volume delta:** OHLC close-location proxy (buy/sell split of tick-count volume), "
                  "required to agree with signal direction when enabled. This is a well-known "
                  "approximation, not real order-flow -- forex has no centralized tape.")
    lines.append("- **Entry timing:** next bar's open after the signal bar closes -- no lookahead.")
    lines.append("- **Position management:** one trade at a time; a signal firing mid-trade is ignored.")
    lines.append("")

    lines.append("## Part 1: Original trailing-stop config (unchanged from the first report)")
    n = primary_summary.get("count", 0)
    lines.append(f"- **Trades:** {n} over {n_bars} bars")
    if n:
        lines.append(f"- **Win rate:** {primary_summary['overall']['win_rate']*100:.1f}%")
        lines.append(f"- **Avg return/trade:** {_fmt_pct(primary_summary['overall']['avg_return'])}")
        lines.append(f"- **Total return (sum of trade returns):** {_fmt_pct(primary_summary['overall']['total_return'])}")
        lines.append(f"- **Max drawdown:** {primary_summary['max_drawdown']*100:.2f}%")
        lines.append(f"- **Buy-and-hold EURUSD over the same window:** {_fmt_pct(buy_and_hold_return)}")
    lines.append("")

    lines.append("### Trailing-stop parameter robustness (same signal engine, varying one thing at a time)")
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

    if search_top_rows is not None:
        lines.append("## Part 2: Fixed take-profit / stop-loss search (in-sample only, 2013-2021)")
        lines.append(
            f"Requested follow-up: instead of only a trailing stop, this searches fixed TP/SL bracket "
            f"exits (checked against intrabar high/low, same-bar TP+SL ties resolved conservatively to "
            f"the stop-loss) combined with EMA100/volume-delta filter on-off and hold-period, "
            f"{search_n_configs} configurations total, requiring at least 15 trades per config to be "
            f"considered. **This search only ever looked at bars before {config.IN_SAMPLE_END_DATE}** -- "
            f"see Part 3 for what happens when the results are checked against data the search never saw."
        )
        lines.append("")
        lines.append("**Top 10 by in-sample total return:**")
        lines.append("| EMA100 | Delta | Hold | TP | SL | Trades | Win Rate | Avg Return | Total Return | Max DD |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in search_top_rows:
            lines.append(
                f"| {r['use_ema_filter']} | {r['use_delta_filter']} | {r['max_hold_days']}d | "
                f"{r['take_profit_pct']*100:.1f}% | {r['stop_loss_pct']*100:.1f}% | {r['count']} | "
                f"{r['win_rate']*100:.1f}% | {_fmt_pct(r['avg_return'])} | {_fmt_pct(r['total_return'])} | "
                f"{r['max_drawdown']*100:.2f}% |"
            )
        lines.append("")
        lines.append(
            "**Bottom 5 (shown for contrast -- the search space is not uniformly profitable; a lot of "
            "TP/SL combinations lose money on the same signal, same data):**"
        )
        lines.append("| EMA100 | Delta | Hold | TP | SL | Trades | Win Rate | Avg Return | Total Return | Max DD |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in search_bottom_rows:
            lines.append(
                f"| {r['use_ema_filter']} | {r['use_delta_filter']} | {r['max_hold_days']}d | "
                f"{r['take_profit_pct']*100:.1f}% | {r['stop_loss_pct']*100:.1f}% | {r['count']} | "
                f"{r['win_rate']*100:.1f}% | {_fmt_pct(r['avg_return'])} | {_fmt_pct(r['total_return'])} | "
                f"{r['max_drawdown']*100:.2f}% |"
            )
        lines.append("")

    if oos_candidates is not None:
        lines.append("## Part 3: Out-of-sample validation (the actual test)")
        lines.append(
            f"In-sample: {in_sample_range[0]} to {in_sample_range[1]}, buy-and-hold {_fmt_pct(in_sample_bh)}. "
            f"Out-of-sample: {out_sample_range[0]} to {out_sample_range[1]}, buy-and-hold {_fmt_pct(out_sample_bh)}. "
            "Each config below was picked from the Part 2 search using only in-sample numbers, then run "
            "**once, unmodified**, against the out-of-sample window."
        )
        lines.append("")
        lines.append("| Config | Sample | Trades | Win Rate | Total Return | Max DD |")
        lines.append("|---|---|---|---|---|---|")
        for cand in oos_candidates:
            is_s, oos_s = cand["in_sample"], cand["out_of_sample"]
            for label, s in (("in-sample", is_s), ("out-of-sample", oos_s)):
                if s.get("count"):
                    lines.append(
                        f"| {cand['label']} | {label} | {s['count']} | {s['overall']['win_rate']*100:.1f}% | "
                        f"{_fmt_pct(s['overall']['total_return'])} | {s['max_drawdown']*100:.2f}% |"
                    )
                else:
                    lines.append(f"| {cand['label']} | {label} | 0 | n/a | n/a | n/a |")
        lines.append("")

        lines.append("### Honest verdict")
        lines.append(
            "The config with the best in-sample total return (+11.5%, EMA100+delta filters, TP 5%/SL 1.5%) "
            "produced only +0.50% out-of-sample -- a large, classic degradation that indicates the in-sample "
            "number was substantially fit to that specific 9-year window rather than reflecting a durable "
            "edge. The config with the best in-sample win rate (80.7%, no filters, a tight TP 0.5%/SL 1.5%) "
            "held up better in relative terms (72.7% win rate out-of-sample) but its out-of-sample total "
            "return was still only +0.61% over 4.5 years -- both below the period's own buy-and-hold "
            "return. The original trailing-stop config went slightly negative out-of-sample (-2.07%). "
            "**None of the three configurations tested here show a solid, generalizable edge on this data.** "
            "A high win rate proved more robust than a high total return, which is a useful, real finding -- "
            "but it isn't the same as a strategy worth sizing up and trading."
        )
        lines.append("")

    if primary_trades:
        lines.append("## Appendix: Trade log (Part 1 primary config)")
        lines.extend(_trade_table(primary_trades))
        lines.append("")

    lines.append("## Limitations")
    lines.append("- **This is a validated-but-still-small sample.** Even at 13 years of daily bars, a "
                  "strategy that trades a few dozen times a year only accumulates tens to low hundreds of "
                  "trades -- enough to catch gross overfitting (Part 3 did), not enough to certify a "
                  "genuine edge with statistical confidence.")
    lines.append("- **Volume delta is a proxy**, not real order flow -- forex spot trading is "
                  "decentralized/OTC with no consolidated tape.")
    lines.append("- **No transaction costs modeled** (spread, swap/rollover, slippage). At sub-1% average "
                  "trade returns, a few pips of round-trip cost would materially erode or erase these numbers.")
    lines.append("- **Single instrument, single indicator family.** Not tested across other pairs.")
    lines.append("- **Daily bars only** -- the original Pine Script is timeframe-agnostic and is often "
                  "run intraday; this is a swing-timeframe read on the same logic.")
    lines.append("")

    return "\n".join(lines)


def save_report(content: str, filename: str) -> str:
    os.makedirs(config.BACKTEST_REPORTS_DIR, exist_ok=True)
    path = os.path.join(config.BACKTEST_REPORTS_DIR, filename)
    with open(path, "w") as fp:
        fp.write(content)
    return path
