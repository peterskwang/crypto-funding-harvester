"""In-sample grid search over TP/SL, trailing width, hold period, and
filter combos. Only ever run against bars before config.IN_SAMPLE_END_DATE
-- the out-of-sample period is validated separately, once, in
validate_oos.py, using whatever config this search selects.

Ranking rule: among configs with at least MIN_TRADES trades (a floor for
"not just 2-3 lucky trades"), rank by total_return. This still overfits to
some degree by construction (420 configs on one 9-year window) -- that's
exactly why the selected config gets re-run on data this search never saw
before it's reported as a result.
"""

import json

from eurusd_strategy import config
from eurusd_strategy.strategy import backtest

MIN_TRADES = 15


def load_in_sample():
    with open(config.DATA_FILE) as fp:
        bars = json.load(fp)
    return [b for b in bars if b["date"] < config.IN_SAMPLE_END_DATE]


def search(bars):
    results = []
    for use_ema in (True, False):
        for use_delta in (True, False):
            for max_hold in (10, 20, 30):
                for tp in (0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05):
                    for sl in (0.005, 0.01, 0.015, 0.02, 0.03):
                        trades = backtest.run_backtest(
                            bars,
                            use_ema_filter=use_ema,
                            use_delta_filter=use_delta,
                            exit_mode="bracket",
                            take_profit_pct=tp,
                            stop_loss_pct=sl,
                            max_hold_days=max_hold,
                        )
                        summary = backtest.summarize_trades(trades)
                        if summary["count"] < MIN_TRADES:
                            continue
                        results.append({
                            "use_ema_filter": use_ema,
                            "use_delta_filter": use_delta,
                            "max_hold_days": max_hold,
                            "take_profit_pct": tp,
                            "stop_loss_pct": sl,
                            "count": summary["count"],
                            "win_rate": summary["overall"]["win_rate"],
                            "avg_return": summary["overall"]["avg_return"],
                            "total_return": summary["overall"]["total_return"],
                            "max_drawdown": summary["max_drawdown"],
                        })
    results.sort(key=lambda r: r["total_return"], reverse=True)
    return results


if __name__ == "__main__":
    bars = load_in_sample()
    print(f"In-sample: {len(bars)} bars, {bars[0]['date']} .. {bars[-1]['date']}")
    results = search(bars)
    print(f"Configs with >= {MIN_TRADES} trades: {len(results)} / 420")
    print()
    print("Top 10 by total_return:")
    for r in results[:10]:
        print(
            f"  ema={r['use_ema_filter']!s:5} delta={r['use_delta_filter']!s:5} "
            f"hold={r['max_hold_days']:2}d tp={r['take_profit_pct']:.3f} sl={r['stop_loss_pct']:.3f} "
            f"-> n={r['count']:3} win={r['win_rate']*100:5.1f}% avg={r['avg_return']*100:6.3f}% "
            f"total={r['total_return']*100:7.2f}% dd={r['max_drawdown']*100:5.2f}%"
        )
    print()
    print("Bottom 5 by total_return (for contrast -- the search space is not uniformly good):")
    for r in results[-5:]:
        print(
            f"  ema={r['use_ema_filter']!s:5} delta={r['use_delta_filter']!s:5} "
            f"hold={r['max_hold_days']:2}d tp={r['take_profit_pct']:.3f} sl={r['stop_loss_pct']:.3f} "
            f"-> n={r['count']:3} win={r['win_rate']*100:5.1f}% avg={r['avg_return']*100:6.3f}% "
            f"total={r['total_return']*100:7.2f}% dd={r['max_drawdown']*100:5.2f}%"
        )

    with open("eurusd_strategy/data/search_results_in_sample.json", "w") as fp:
        json.dump(results, fp, indent=2)
