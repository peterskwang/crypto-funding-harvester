"""Backtests the screener's scoring rules against realized IPO price history.

Run from the repo root as:
    python -m pre_ipo_screener.run_backtest --start 2025-07-09 --end 2026-07-09

Requires POLYGON_API_KEY or FMP_API_KEY (whichever is set in the environment
is used -- Polygon is preferred if both are) and network access to that
provider's API domain. This pulls a full year (or whatever range you give it)
of daily bars per candidate, which is a lot of API calls -- see
pre_ipo_screener/README.md for current data-access status.
"""
from __future__ import annotations

import argparse
import datetime as dt

from pre_ipo_screener.data.client_factory import NoDataSourceConfigured, get_client
from pre_ipo_screener.data.fmp_client import FMPAuthError, FMPClient
from pre_ipo_screener.data.polygon_client import PolygonAuthError
from pre_ipo_screener.screener import backtest, historical, report, universe
from utils.logger import configure_logging


def run(client, logger, start_date: dt.date, end_date: dt.date) -> str:
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

    data_source = "FMP (live)" if isinstance(client, FMPClient) else "Polygon.io (live)"
    content = report.render_backtest_report(trades, summary, start_date, end_date, data_source=data_source)
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

    try:
        client = get_client()
        path = run(client, logger, start_date, end_date)
    except (NoDataSourceConfigured, PolygonAuthError, FMPAuthError) as exc:
        logger.error(str(exc))
        raise SystemExit(1) from exc

    logger.info("Backtest report saved to %s", path)


if __name__ == "__main__":
    main()
