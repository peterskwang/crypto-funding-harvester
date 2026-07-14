"""Entrypoint: runs the primary backtest config plus a parameter robustness
sweep against real EURUSD daily bars, then renders and saves a markdown
report. Usage: python -m eurusd_strategy.run_backtest
"""

import datetime as dt
import json

from eurusd_strategy import config
from eurusd_strategy.strategy import backtest, report


def main():
    with open(config.DATA_FILE) as fp:
        bars = json.load(fp)

    closes = [b["close"] for b in bars]
    buy_and_hold_return = (closes[-1] - closes[0]) / closes[0]

    primary_trades = backtest.run_backtest(bars, use_ema_filter=True, use_delta_filter=True)
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

    content = report.render_report(
        primary_summary=primary_summary,
        primary_trades=primary_trades,
        robustness_rows=robustness_rows,
        buy_and_hold_return=buy_and_hold_return,
        data_start=bars[0]["date"],
        data_end=bars[-1]["date"],
        n_bars=len(bars),
    )

    today = dt.date.today().isoformat()
    filename = f"{today}_eurusd_velocity_accel_backtest.md"
    path = report.save_report(content, filename)

    print(f"Saved report to {path}")
    print()
    print(f"Primary config: {primary_summary['count']} trades, "
          f"win_rate={primary_summary['overall']['win_rate']*100:.1f}%, "
          f"total_return={primary_summary['overall']['total_return']*100:.2f}%, "
          f"buy_and_hold={buy_and_hold_return*100:.2f}%")


if __name__ == "__main__":
    main()
