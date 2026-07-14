"""Entrypoint: runs the original trailing-stop config plus its parameter
robustness sweep, the in-sample TP/SL grid search, and out-of-sample
validation, then renders and saves one combined markdown report.
Usage: python -m eurusd_strategy.run_backtest
"""

import datetime as dt
import json

from eurusd_strategy import config
from eurusd_strategy.search_tp_sl import MIN_TRADES, load_in_sample, search
from eurusd_strategy.strategy import backtest, report
from eurusd_strategy.validate_oos import CANDIDATES


def main():
    with open(config.DATA_FILE) as fp:
        bars = json.load(fp)

    closes = [b["close"] for b in bars]
    buy_and_hold_return = (closes[-1] - closes[0]) / closes[0]

    # -- Part 1: original trailing-stop config + robustness sweep --
    primary_trades = backtest.run_backtest(
        bars, use_ema_filter=True, use_delta_filter=True, exit_mode="trailing"
    )
    primary_summary = backtest.summarize_trades(primary_trades)

    sweep_specs = [
        ("Raw signal (no EMA100, no delta)", dict(use_ema_filter=False, use_delta_filter=False)),
        ("+ EMA100 trend filter only", dict(use_ema_filter=True, use_delta_filter=False)),
        ("+ Volume delta filter only", dict(use_ema_filter=False, use_delta_filter=True)),
        ("Primary (EMA100 + delta)", dict(use_ema_filter=True, use_delta_filter=True)),
        ("Trail 1.0%", dict(trailing_stop_pct=0.01)),
        ("Trail 1.5%", dict(trailing_stop_pct=0.015)),
        ("Trail 3.0%", dict(trailing_stop_pct=0.03)),
        ("Trail 5.0%", dict(trailing_stop_pct=0.05)),
        ("Max hold 10d", dict(max_hold_days=10)),
        ("Max hold 15d", dict(max_hold_days=15)),
        ("Max hold 30d", dict(max_hold_days=30)),
        ("Max hold 45d", dict(max_hold_days=45)),
    ]
    robustness_rows = []
    for label, kwargs in sweep_specs:
        kwargs.setdefault("use_ema_filter", True)
        kwargs.setdefault("use_delta_filter", True)
        kwargs.setdefault("exit_mode", "trailing")
        trades = backtest.run_backtest(bars, **kwargs)
        summary = backtest.summarize_trades(trades)
        row = {"label": label, "count": summary["count"]}
        if summary["count"]:
            row.update({
                "win_rate": summary["overall"]["win_rate"],
                "avg_return": summary["overall"]["avg_return"],
                "total_return": summary["overall"]["total_return"],
                "max_drawdown": summary["max_drawdown"],
            })
        robustness_rows.append(row)

    # -- Part 2: in-sample TP/SL search --
    in_sample_bars = load_in_sample()
    search_results = search(in_sample_bars)

    # -- Part 3: out-of-sample validation --
    out_sample_bars = [b for b in bars if b["date"] >= config.IN_SAMPLE_END_DATE]
    closes_is = [b["close"] for b in in_sample_bars]
    closes_oos = [b["close"] for b in out_sample_bars]
    in_sample_bh = (closes_is[-1] - closes_is[0]) / closes_is[0]
    out_sample_bh = (closes_oos[-1] - closes_oos[0]) / closes_oos[0]

    oos_candidates = []
    for cand in CANDIDATES:
        trades_is = backtest.run_backtest(in_sample_bars, **cand["kwargs"])
        trades_oos = backtest.run_backtest(out_sample_bars, **cand["kwargs"])
        oos_candidates.append({
            "label": cand["label"],
            "in_sample": backtest.summarize_trades(trades_is),
            "out_of_sample": backtest.summarize_trades(trades_oos),
        })

    content = report.render_report(
        primary_summary=primary_summary,
        primary_trades=primary_trades,
        robustness_rows=robustness_rows,
        buy_and_hold_return=buy_and_hold_return,
        data_start=bars[0]["date"],
        data_end=bars[-1]["date"],
        n_bars=len(bars),
        search_top_rows=search_results[:10],
        search_bottom_rows=search_results[-5:],
        search_n_configs=len(search_results),
        oos_candidates=oos_candidates,
        in_sample_range=(in_sample_bars[0]["date"], in_sample_bars[-1]["date"]),
        out_sample_range=(out_sample_bars[0]["date"], out_sample_bars[-1]["date"]),
        in_sample_bh=in_sample_bh,
        out_sample_bh=out_sample_bh,
    )

    today = dt.date.today().isoformat()
    filename = f"{today}_eurusd_velocity_accel_backtest.md"
    path = report.save_report(content, filename)

    print(f"Saved report to {path}")
    print()
    print(f"Part 1 (trailing, EMA+delta): {primary_summary['count']} trades, "
          f"total_return={primary_summary['overall']['total_return']*100:.2f}%, "
          f"buy_and_hold={buy_and_hold_return*100:.2f}%")
    print(f"Part 2: {len(search_results)} configs with >= {MIN_TRADES} trades")
    for cand in oos_candidates:
        oos = cand["out_of_sample"]
        print(f"Part 3: {cand['label']}: OOS total_return="
              f"{oos['overall']['total_return']*100 if oos.get('count') else 0:.2f}%")


if __name__ == "__main__":
    main()
