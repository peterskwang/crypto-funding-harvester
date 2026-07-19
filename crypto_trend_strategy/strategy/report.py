"""Renders the crypto trend-following strategy report."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from crypto_trend_strategy import config

DISCLAIMER = (
    "**Not investment advice.** This is a rules-based, vol-targeted "
    "multi-asset trend-following backtest on real daily crypto price data "
    "(2018-2026). Every number below, including the out-of-sample section, "
    "is a backtest artifact, not a live track record."
)


def _fmt_pct(x):
    return f"{x * 100:+.1f}%" if x is not None else "n/a"


def render_report(
    is_summary: Dict[str, Any],
    oos_summary: Dict[str, Any],
    full_summary: Dict[str, Any],
    year_by_year: List[Dict[str, Any]],
    bh_comparison: Dict[str, Any],
) -> str:
    lines = []
    lines.append("# Crypto Multi-Asset Trend-Following Strategy -- Backtest Report")
    lines.append("")
    lines.append(DISCLAIMER)
    lines.append("")

    lines.append("## Why this project exists")
    lines.append(
        "A rigorous 36-pair G10 FX cointegration sweep (see `fx_statarb_strategy/`) found "
        "zero pairs survive proper multiple-testing correction -- FX spot pairs trading was "
        "ruled out on the evidence, not under-tuned. An external quant-strategist review "
        "recommended pivoting to time-series (trend-following) momentum -- the most robust, "
        "most replicable strategy family in the literature -- applied to a higher-volatility "
        "asset class where genuine return potential is structurally larger than G10 FX spot. "
        "Crypto perpetual funding-rate arbitrage (the closer match to this repo's original "
        "strategy) was considered first but ruled out on data-access grounds: this "
        "environment blocks direct Binance access and FMP has no funding-rate history "
        "endpoint, so it can't be backtested honestly here."
    )
    lines.append("")

    lines.append("## Methodology")
    lines.append(f"- **Universe:** {', '.join(config.SYMBOLS)} (11 liquid coins, dynamic "
                  "universe -- each joins once it has its own price history, same as a live system).")
    lines.append(f"- **Signal:** blended time-series momentum across {config.MOMENTUM_LOOKBACKS_DAYS} "
                  "day lookbacks, each risk-adjusted by trailing realized vol before averaging "
                  "(so a 30-day and a 200-day window contribute on a comparable scale).")
    lines.append(f"- **Sizing:** volatility-targeted per asset ({config.TARGET_ANNUALIZED_VOL_PER_ASSET*100:.0f}% "
                  f"annualized vol target each, capped at {config.MAX_ASSET_WEIGHT*100:.0f}% portfolio weight), "
                  f"portfolio gross exposure capped at {config.GROSS_EXPOSURE_CAP}x.")
    lines.append(f"- **Exit:** signal-flip (classic trend-following, no fixed take-profit) "
                  f"plus a {config.STOP_LOSS_PCT*100:.0f}% stop-loss backstop sized to crypto's own "
                  "realized volatility (BTC ~65% annualized, alts up to 170%+) -- a backstop for "
                  "when the trend signal is too slow to react to a sudden crash, not the primary risk control.")
    lines.append(f"- **Costs:** {config.TRANSACTION_COST_PCT*100:.2f}% one-way on every position change (turnover-based).")
    lines.append(f"- **Split:** in-sample {config.BACKTEST_START_DATE} to {config.IN_SAMPLE_END_DATE} "
                  f"(design/calibration), out-of-sample {config.IN_SAMPLE_END_DATE} onward (touched once, "
                  "not re-tuned after seeing it). No parameter grid search was run -- lookbacks, vol "
                  "target, and stop-loss were each chosen once from the data's own statistics, not swept.")
    lines.append("")

    lines.append("## Results")
    lines.append("| Period | CAGR | Sharpe | Max Drawdown | Total Return |")
    lines.append("|---|---|---|---|---|")
    for label, s in [("In-sample", is_summary), ("Out-of-sample", oos_summary), ("Full 2018-2026", full_summary)]:
        if s.get("count"):
            lines.append(f"| {label} | {_fmt_pct(s['cagr'])} | {s['sharpe']:.2f} | "
                          f"{s['max_drawdown']*100:.1f}% | {_fmt_pct(s['total_return'])} |")
    lines.append("")

    lines.append("### Honest verdict")
    lines.append(
        f"In-sample looked spectacular: {_fmt_pct(is_summary['cagr'])} CAGR, Sharpe "
        f"{is_summary['sharpe']:.2f}. **Out-of-sample the strategy actually lost money**: "
        f"{_fmt_pct(oos_summary['cagr'])} CAGR, Sharpe {oos_summary['sharpe']:.2f}, total "
        f"return {_fmt_pct(oos_summary['total_return'])} over the held-out period. This is "
        "exactly the failure mode walk-forward validation exists to catch, and it caught it."
    )
    lines.append("")
    lines.append(
        f"**The year-by-year breakdown explains why**: 2021 alone returned "
        f"{next(y['return'] for y in year_by_year if y['year']=='2021')} -- one historic "
        "crypto bull-market year is doing nearly all the work in the in-sample number. Every "
        "other year is decidedly mixed:"
    )
    lines.append("")
    lines.append("| Year | Return |")
    lines.append("|---|---|")
    for y in year_by_year:
        lines.append(f"| {y['year']} | {y['return']} |")
    lines.append("")
    lines.append(
        "2022, 2023, and 2025 were all significant losing years (-33%, -9%, -37%); only 2024 "
        "and 2026-YTD were modestly positive. This is not a repeatable monthly edge -- it's "
        "one extraordinary regime (2020-2021 mania) followed by years of whipsaw and mixed "
        "results, which is a well-documented characteristic of trend-following: it captures "
        "sustained directional moves and bleeds slowly (or gets stopped out) in choppy, "
        "range-bound, or sharply-reversing markets."
    )
    lines.append("")

    lines.append("### The number that matters most: versus doing nothing")
    lines.append("| Period | Strategy | BTC buy-and-hold | ETH buy-and-hold |")
    lines.append("|---|---|---|---|")
    for label, key in [("Full 2018-2026", "full"), ("In-sample", "is"), ("Out-of-sample", "oos")]:
        c = bh_comparison[key]
        lines.append(f"| {label} | {_fmt_pct(c['strategy'])} | {_fmt_pct(c['btc'])} | {_fmt_pct(c['eth'])} |")
    lines.append("")
    lines.append(
        f"**Over the out-of-sample window -- the only honest forward-looking test -- simply "
        f"buying and holding BTC returned {_fmt_pct(bh_comparison['oos']['btc'])} while this "
        f"strategy returned {_fmt_pct(bh_comparison['oos']['strategy'])}.** The vol-targeted "
        "trend book did not just fail to hit an ambitious target -- it destroyed value "
        "relative to the simplest possible alternative, during a period that was actually a "
        "strong bull market. The strategy's apparent edge over buy-and-hold in the full-sample "
        "number is entirely a 2021 artifact."
    )
    lines.append("")

    lines.append("## What this means for the original 5%/month goal")
    lines.append(
        "Two structurally different, legitimate strategy families have now been tested with "
        "real rigor on real data: FX pairs cointegration (ruled out -- no pair in the entire "
        "G10 set survives multiple-testing correction) and crypto trend-following (tested "
        "here -- real full-sample returns, but they evaporate out-of-sample and underperform "
        "simple buy-and-hold in the most recent, most relevant period). Neither supports a "
        "5%/month, consistently-achievable claim. This matches the external quant-strategist "
        "review's assessment: realistic systematic strategies at reasonable risk deliver "
        "high-single to low-double-digit annual returns at Sharpe ~0.5-1.0, not 80%/year. "
        "The honest path forward, if this is worth continuing, is either (a) accept a "
        "realistic target and size positions/leverage accordingly, or (b) if crypto exposure "
        "is the goal, seriously compare this strategy against simple buy-and-hold before "
        "adding the complexity, cost, and whipsaw risk of active trend-following on top of it."
    )
    lines.append("")

    lines.append("## Limitations")
    lines.append("- **One out-of-sample period, one asset class.** 3.5 years is a real forward "
                  "test but still a single historical path -- crypto has had few full market cycles.")
    lines.append("- **No slippage/liquidity modeling** beyond a flat 10bps cost -- in a sharp "
                  "crash, real fills on smaller-cap alts (DOGE, AVAX, DOT) would likely be worse.")
    lines.append("- **Survivorship**: the 11-coin universe is today's liquid majors, not a "
                  "point-in-time-correct universe of what was liquid/tradeable in 2018.")
    lines.append("- **No borrow/funding costs modeled for short positions** -- shorting crypto "
                  "in practice carries real, sometimes substantial, funding costs this backtest ignores.")
    lines.append("")

    return "\n".join(lines)


def save_report(content: str, filename: str) -> str:
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    path = os.path.join(config.REPORTS_DIR, filename)
    with open(path, "w") as fp:
        fp.write(content)
    return path
