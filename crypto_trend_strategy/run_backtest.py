"""Entrypoint: runs the in-sample/out-of-sample crypto trend-following
backtest, computes the buy-and-hold comparison, and saves the report.
Usage: python -m crypto_trend_strategy.run_backtest
"""

import datetime as dt

from crypto_trend_strategy import config
from crypto_trend_strategy.strategy import backtest, data, report


def _bh_return(all_bars, symbol, start, end):
    bars = [b for b in all_bars[symbol] if start <= b["date"][:10] <= end]
    if len(bars) < 2:
        return None
    return bars[-1]["close"] / bars[0]["close"] - 1


def main():
    all_bars = data.load_all(config.BACKTEST_START_DATE)
    calendar = data.common_calendar(all_bars)

    full_result = backtest.run_backtest(all_bars, calendar)
    full_summary = backtest.summarize(full_result)

    is_result = backtest.run_backtest(all_bars, calendar, start_date=config.BACKTEST_START_DATE, end_date=config.IN_SAMPLE_END_DATE)
    is_summary = backtest.summarize(is_result)

    oos_result = backtest.run_backtest(all_bars, calendar, start_date=config.IN_SAMPLE_END_DATE)
    oos_summary = backtest.summarize(oos_result)

    # year-by-year breakdown (from the full-sample equity curve)
    curve = full_result["equity_curve"]
    by_year_last = {}
    for point in curve:
        by_year_last[point["date"][:4]] = point["equity"]
    year_by_year = []
    prev_end = config.INITIAL_CAPITAL
    for year in sorted(by_year_last):
        end_eq = by_year_last[year]
        ret = end_eq / prev_end - 1
        year_by_year.append({"year": year, "return": f"{ret*100:+.1f}%"})
        prev_end = end_eq

    bh_comparison = {
        "full": {
            "strategy": full_summary["total_return"],
            "btc": _bh_return(all_bars, "BTCUSD", config.BACKTEST_START_DATE, calendar[-1]),
            "eth": _bh_return(all_bars, "ETHUSD", config.BACKTEST_START_DATE, calendar[-1]),
        },
        "is": {
            "strategy": is_summary["total_return"],
            "btc": _bh_return(all_bars, "BTCUSD", config.BACKTEST_START_DATE, config.IN_SAMPLE_END_DATE),
            "eth": _bh_return(all_bars, "ETHUSD", config.BACKTEST_START_DATE, config.IN_SAMPLE_END_DATE),
        },
        "oos": {
            "strategy": oos_summary["total_return"],
            "btc": _bh_return(all_bars, "BTCUSD", config.IN_SAMPLE_END_DATE, calendar[-1]),
            "eth": _bh_return(all_bars, "ETHUSD", config.IN_SAMPLE_END_DATE, calendar[-1]),
        },
    }

    content = report.render_report(is_summary, oos_summary, full_summary, year_by_year, bh_comparison)
    today = dt.date.today().isoformat()
    filename = f"{today}_crypto_trend_backtest.md"
    path = report.save_report(content, filename)

    print(f"Saved report to {path}")
    print(f"In-sample:     CAGR={is_summary['cagr']*100:.1f}%  Sharpe={is_summary['sharpe']:.2f}  MaxDD={is_summary['max_drawdown']*100:.1f}%")
    print(f"Out-of-sample: CAGR={oos_summary['cagr']*100:.1f}%  Sharpe={oos_summary['sharpe']:.2f}  MaxDD={oos_summary['max_drawdown']*100:.1f}%")
    print(f"OOS strategy vs BTC buy-and-hold: {oos_summary['total_return']*100:+.1f}% vs {bh_comparison['oos']['btc']*100:+.1f}%")


if __name__ == "__main__":
    main()
