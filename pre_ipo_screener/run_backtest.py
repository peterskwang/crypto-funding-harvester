"""Backtests the screener's scoring rules against realized IPO price history.

Run from the repo root as:
    python -m pre_ipo_screener.run_backtest --start 2025-07-09 --end 2026-07-09

Requires POLYGON_API_KEY and network access to api.polygon.io — this pulls a
full year (or whatever range you give it) of daily bars per candidate, which
is a lot of API calls. There is currently no live data path that supplies
this (Polygon is network-blocked in this environment, and FMP's free tier
blocks all price/quote endpoints) -- see pre_ipo_screener/README.md.
"""
from __future__ import annotations

import argparse
import datetime as dt

from pre_ipo_screener.data.polygon_client import PolygonAuthError, PolygonClient
from pre_ipo_screener.screener import backtest, historical, report, universe
from utils.logger import configure_logging


def run(client: PolygonClient, logger, start_date: dt.date, end_date: dt.date) -> str:
    candidates = universe.build_universe_for_range(client, start_date, end_date)
    logger.info("Backtest universe: %d candidates between %s and %s", len(candidates), start_date, end_date)

    candidates_with_bars = []
    for candidate in candidates:
        candidate["sector_tag"] = historical.get_sector_tag(client, candidate)
        candidate = historical.compute_post_ipo_performance(client, candidate, today=end_date)
        candidates_with_bars.append(candidate)

    trades = backtest.run_backtest(candidates_with_bars)
    summary = backtest.summarize_trades(trades)
    logger.info("Backtest complete: %d trades simulated", len(trades))

    content = report.render_backtest_report(trades, summary, start_date, end_date, data_source="Polygon.io (live)")
    return report.save_backtest_report(content, start_date, end_date)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-IPO screener backtest")
    today = dt.date.today()
    parser.add_argument("--start", type=str, default=(today - dt.timedelta(days=365)).isoformat())
    parser.add_argument("--end", type=str, default=today.isoformat())
    args = parser.parse_args()

    logger = configure_logging()
    start_date = dt.date.fromisoformat(args.start)
    end_date = dt.date.fromisoformat(args.end)
    client = PolygonClient()

    try:
        path = run(client, logger, start_date, end_date)
    except PolygonAuthError as exc:
        logger.error(str(exc))
        raise SystemExit(1) from exc

    logger.info("Backtest report saved to %s", path)


if __name__ == "__main__":
    main()
