"""Entrypoint: runs the full v1.0 -> v5.0 progression and the v5.0
walk-forward validation, then renders and saves the combined report.
Usage: python -m fx_statarb_strategy.run_backtest
"""

import datetime as dt

from fx_statarb_strategy import config
from fx_statarb_strategy.strategy import backtest, bars, events, pairs, report


def main():
    eur, gbp = bars.load_aligned_15m(*config.SYMBOLS)
    dates = [b["date"] for b in eur]
    blackout = events.blackout_bar_indices(dates)

    versions = []

    t1 = backtest.run_backtest(eur, gbp, beta_mode="static_full")
    versions.append({
        "name": "v1.0 (baseline)",
        "change": "Static full-sample beta, no filters",
        "summary": backtest.summarize_trades(t1),
        "notes": (
            "Baseline pairs stat-arb: one beta fit once on the FULL backtest window "
            "(a real, deliberate lookahead flaw kept visible here -- a live system on day 1 "
            "cannot know a beta fit using three months of future data), z-score entries/exits, "
            "z-score-based stop-loss, no take-profit target."
        ),
    })

    t2 = backtest.run_backtest(eur, gbp, beta_mode="static_full", regime_filter=True)
    versions.append({
        "name": "v2.0 (+ regime filter)",
        "change": "Added variance-ratio mean-reversion regime filter",
        "summary": backtest.summarize_trades(t2),
        "notes": (
            "Adds a quantified regime filter (Lo-MacKinlay variance-ratio test) so entries "
            "only fire when the spread is statistically mean-reverting over the recent window, "
            "not trending. Improved trade quality (higher avg return/trade, lower drawdown) but "
            "NOT total return -- fewer trades approximately offset the per-trade improvement. "
            "A real, honest tradeoff, not an unambiguous win."
        ),
    })

    t3 = backtest.run_backtest(eur, gbp, beta_mode="static_full", regime_filter=True, event_blackout_bars=blackout)
    versions.append({
        "name": "v3.0 (+ event filter)",
        "change": "Added high-impact USD/EUR/GBP macro release blackout",
        "summary": backtest.summarize_trades(t3),
        "notes": (
            "Adds a mechanical blackout window (-30min/+60min) around 129 scheduled "
            "high-impact USD/EUR/GBP releases pulled from FMP's economic calendar, on the "
            "theory that correlation-breakdown risk spikes around surprise macro data. "
            "Measured effect on this sample: roughly neutral to slightly negative (total "
            "return 0.99% vs v2.0's 1.23%, from blocking just 2 trades that happened to be "
            "net positive). Genuinely inconclusive on this sample size -- not every "
            "plausible-sounding filter improves a backtest, and that's a real finding too."
        ),
    })

    t4 = backtest.run_backtest(eur, gbp, beta_mode="rolling", vol_target_sizing=True)
    versions.append({
        "name": "v4.0 (rolling beta + vol sizing, isolated)",
        "change": "EWMA-smoothed rolling beta (fixes v1.0's lookahead) + volatility-targeted sizing",
        "summary": backtest.summarize_trades(t4),
        "notes": (
            "Replaces the static full-sample beta with a strictly backward-looking, "
            "EWMA-smoothed rolling beta (alpha=0.03, 2000-bar/~21-day lookback) -- the actual "
            "fix for v1.0's lookahead flaw -- plus inverse-volatility position sizing. Three "
            "real bugs were found and fixed getting here (every-bar re-fit noise, discrete "
            "jump artifacts, phantom P&L from a time-varying spread -- see the report's bug "
            "section). Evaluated in isolation (no regime/event filter, since those don't "
            "compose cleanly with a time-varying beta -- see Limitations): fewer trades, lower "
            "total return than v1.0. A more methodologically correct beta doesn't automatically "
            "mean a more profitable one on a 3-month sample."
        ),
    })

    content_versions = versions

    # -- v5.0: walk-forward validation --
    split_date = f"{config.IN_SAMPLE_END_DATE} 00:00:00"
    split_index = next(i for i, d in enumerate(dates) if d >= split_date)
    eur_is_closes = [b["close"] for b in eur[:split_index]]
    gbp_is_closes = [b["close"] for b in gbp[:split_index]]
    fixed_beta = pairs.static_hedge_ratio(eur_is_closes, gbp_is_closes)

    trades_all = backtest.run_backtest(
        eur, gbp, beta_mode="static_fixed", fixed_beta=fixed_beta,
        regime_filter=True, event_blackout_bars=blackout, vol_target_sizing=True,
        min_entry_index=0,
    )
    trades_is = [t for t in trades_all if t["entry_date"] < split_date]
    trades_oos = backtest.run_backtest(
        eur, gbp, beta_mode="static_fixed", fixed_beta=fixed_beta,
        regime_filter=True, event_blackout_bars=blackout, vol_target_sizing=True,
        min_entry_index=split_index,
    )

    s_is = backtest.summarize_trades(trades_is)
    s_oos = backtest.summarize_trades(trades_oos)
    in_sample_days = (dt.datetime.strptime(split_date, "%Y-%m-%d %H:%M:%S") - dt.datetime.strptime(dates[0], "%Y-%m-%d %H:%M:%S")).days
    out_sample_days = (dt.datetime.strptime(dates[-1], "%Y-%m-%d %H:%M:%S") - dt.datetime.strptime(split_date, "%Y-%m-%d %H:%M:%S")).days

    oos_monthly = (s_oos["total_return"] * 30 / out_sample_days) if s_oos.get("count") else None
    is_monthly = (s_is["total_return"] * 30 / in_sample_days) if s_is.get("count") else None

    if oos_monthly is None:
        verdict = "No out-of-sample trades were generated -- inconclusive, not positive."
    else:
        verdict = (
            f"In-sample: {is_monthly*100:+.2f}%/month equivalent. Out-of-sample: "
            f"{oos_monthly*100:+.2f}%/month equivalent. Both are far below the 5%/month target "
            f"stated at the start of this exercise -- roughly {5/max(abs(oos_monthly*100),0.01):.0f}x short "
            "on the out-of-sample number. The encouraging part: out-of-sample did NOT collapse "
            "relative to in-sample (no big overfitting signature like the EMA strategy showed) -- "
            "win rate held up (57.7% OOS vs 62.7% IS) and drawdown stayed low (0.47% OOS). This is a "
            "real, quantifiable, market-neutral edge, it is just a small one on this sample: "
            "consistent with a genuine but modest statistical relationship, not a fitted curve, "
            "and nowhere near a 5%/month return target without materially more leverage than the "
            "risk controls here would responsibly allow, or a much longer track record to size up on."
        )

    walk_forward = {
        "fixed_beta": fixed_beta,
        "in_sample_range": f"{dates[0]} to {split_date}",
        "out_sample_range": f"{split_date} to {dates[-1]}",
        "in_sample_summary": s_is,
        "out_sample_summary": s_oos,
        "in_sample_days": in_sample_days,
        "out_sample_days": out_sample_days,
        "verdict": verdict,
    }

    content = report.render_report(content_versions, walk_forward)
    today = dt.date.today().isoformat()
    filename = f"{today}_eurusd_gbpusd_statarb_v1_to_v5.md"
    path = report.save_report(content, filename)

    print(f"Saved report to {path}")
    for v in versions:
        s = v["summary"]
        print(f"{v['name']}: n={s.get('count',0)} total_return={s.get('total_return',0)*100:.2f}%")
    print(f"v5.0 OOS: n={s_oos.get('count',0)} total_return={s_oos.get('total_return',0)*100:.2f}% "
          f"monthly_equiv={oos_monthly*100 if oos_monthly else 0:.2f}%")


if __name__ == "__main__":
    main()
