"""Runs a fixed set of configs -- selected from search_tp_sl.py's in-sample
results -- against the out-of-sample window (2022-01-03..2026-07-14), which
the search never touched. This is the actual test of whether the in-sample
search found something real or just fit noise. Nothing here is re-tuned
after seeing these numbers.
"""

import json

from eurusd_strategy import config
from eurusd_strategy.strategy import backtest

# Selected from search_tp_sl.py's in-sample top results: the single best by
# total_return, plus the best by win_rate among configs with a comparable
# trade count (a higher-win-rate / lower-drawdown pattern is less likely to
# be a couple of lucky trades than a low-win-rate / high-total-return one).
CANDIDATES = [
    {
        "label": "Best in-sample total_return (EMA+delta, hold=20d, tp=5%, sl=1.5%)",
        "kwargs": dict(use_ema_filter=True, use_delta_filter=True, exit_mode="bracket",
                       take_profit_pct=0.05, stop_loss_pct=0.015, max_hold_days=20),
    },
    {
        "label": "Best in-sample win_rate (no filters, hold=20d, tp=0.5%, sl=1.5%)",
        "kwargs": dict(use_ema_filter=False, use_delta_filter=False, exit_mode="bracket",
                       take_profit_pct=0.005, stop_loss_pct=0.015, max_hold_days=20),
    },
    {
        "label": "Original trailing-stop config (from first report, unchanged)",
        "kwargs": dict(use_ema_filter=True, use_delta_filter=True, exit_mode="trailing",
                       trailing_stop_pct=0.02, max_hold_days=20),
    },
]


def main():
    with open(config.DATA_FILE) as fp:
        bars = json.load(fp)
    in_sample = [b for b in bars if b["date"] < config.IN_SAMPLE_END_DATE]
    out_sample = [b for b in bars if b["date"] >= config.IN_SAMPLE_END_DATE]

    closes_oos = [b["close"] for b in out_sample]
    bh_oos = (closes_oos[-1] - closes_oos[0]) / closes_oos[0]
    closes_is = [b["close"] for b in in_sample]
    bh_is = (closes_is[-1] - closes_is[0]) / closes_is[0]

    print(f"In-sample:     {in_sample[0]['date']} .. {in_sample[-1]['date']} ({len(in_sample)} bars), buy&hold={bh_is*100:+.2f}%")
    print(f"Out-of-sample: {out_sample[0]['date']} .. {out_sample[-1]['date']} ({len(out_sample)} bars), buy&hold={bh_oos*100:+.2f}%")
    print()

    results = []
    for cand in CANDIDATES:
        trades_is = backtest.run_backtest(in_sample, **cand["kwargs"])
        summary_is = backtest.summarize_trades(trades_is)
        trades_oos = backtest.run_backtest(out_sample, **cand["kwargs"])
        summary_oos = backtest.summarize_trades(trades_oos)

        print(f"--- {cand['label']} ---")
        print(f"  IN-SAMPLE:  n={summary_is.get('count',0):3} "
              f"win={summary_is.get('overall',{}).get('win_rate',0)*100 if summary_is.get('count') else 0:5.1f}% "
              f"total={summary_is.get('overall',{}).get('total_return',0)*100 if summary_is.get('count') else 0:7.2f}% "
              f"dd={summary_is.get('max_drawdown',0)*100 if summary_is.get('count') else 0:5.2f}%")
        print(f"  OUT-SAMPLE: n={summary_oos.get('count',0):3} "
              f"win={summary_oos.get('overall',{}).get('win_rate',0)*100 if summary_oos.get('count') else 0:5.1f}% "
              f"total={summary_oos.get('overall',{}).get('total_return',0)*100 if summary_oos.get('count') else 0:7.2f}% "
              f"dd={summary_oos.get('max_drawdown',0)*100 if summary_oos.get('count') else 0:5.2f}%")
        print()

        results.append({
            "label": cand["label"], "kwargs": cand["kwargs"],
            "in_sample": summary_is, "out_of_sample": summary_oos,
            "in_sample_trades": trades_is, "out_of_sample_trades": trades_oos,
        })

    with open("eurusd_strategy/data/oos_validation_results.json", "w") as fp:
        json.dump(results, fp, indent=2, default=str)


if __name__ == "__main__":
    main()
