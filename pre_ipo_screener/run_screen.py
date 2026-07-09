"""Cron-friendly entrypoint for the pre-IPO screener.

Run from the repo root as:
    python -m pre_ipo_screener.run_screen --mode weekly
    python -m pre_ipo_screener.run_screen --mode daily
"""
from __future__ import annotations

import argparse
import datetime as dt

from pre_ipo_screener import config
from pre_ipo_screener.data.polygon_client import PolygonAuthError, PolygonClient
from pre_ipo_screener.screener import historical, report, scoring, universe
from utils.logger import configure_logging
from utils.state import load_state, save_state


def _annotate_sector(client: PolygonClient, candidates: list) -> list:
    for candidate in candidates:
        candidate["sector_tag"] = historical.get_sector_tag(client, candidate)
    return candidates


def _score_shorts(recent_with_perf: list, today: dt.date) -> list:
    flagged = scoring.score_fade_candidates(recent_with_perf, today)
    for candidate in flagged:
        candidate["suggested_style"] = scoring.suggested_style(candidate)
    return scoring.rank_candidates(flagged, key="conviction")


def run_weekly(client: PolygonClient, logger, today: dt.date):
    upcoming = universe.build_upcoming_universe(client, today)
    recent = universe.build_recent_universe(client, today)
    logger.info("Universe sizes: upcoming=%d recent=%d", len(upcoming), len(recent))

    recent_with_perf = [historical.compute_post_ipo_performance(client, c, today) for c in recent]
    recent_with_perf = _annotate_sector(client, recent_with_perf)
    analog_groups = historical.build_analog_groups(recent_with_perf, client)

    upcoming = _annotate_sector(client, upcoming)
    scored_long = [scoring.score_upcoming(c, analog_groups, today) for c in upcoming]
    long_candidates = scoring.rank_candidates(scored_long, key="score")
    short_candidates = _score_shorts(recent_with_perf, today)

    content = report.render_report(long_candidates, short_candidates, analog_groups, today, mode="weekly")
    path = report.save_report(content, today)

    save_state(
        config.STATE_FILE_PATH,
        {
            "last_weekly_run": today.isoformat(),
            "upcoming_universe": upcoming,
            "analog_groups": analog_groups,
        },
    )
    return content, path, long_candidates, short_candidates


def run_daily(client: PolygonClient, logger, today: dt.date):
    state = load_state(config.STATE_FILE_PATH)
    upcoming = state.get("upcoming_universe") or []
    analog_groups = state.get("analog_groups") or {}

    if not upcoming:
        logger.warning("No cached weekly universe found — running a full weekly scan instead")
        return run_weekly(client, logger, today)

    scored_long = [scoring.score_upcoming(c, analog_groups, today) for c in upcoming]
    long_candidates = scoring.rank_candidates(scored_long, key="score")

    recent = universe.build_recent_universe(client, today)
    recent_with_perf = [historical.compute_post_ipo_performance(client, c, today) for c in recent]
    short_candidates = _score_shorts(recent_with_perf, today)

    content = report.render_report(long_candidates, short_candidates, analog_groups, today, mode="daily")
    path = report.save_report(content, today)
    return content, path, long_candidates, short_candidates


def main() -> None:
    parser = argparse.ArgumentParser(description="Pre-IPO screener")
    parser.add_argument("--mode", choices=["weekly", "daily"], default="weekly")
    args = parser.parse_args()

    logger = configure_logging()
    today = dt.date.today()
    client = PolygonClient()

    try:
        if args.mode == "weekly":
            content, path, longs, shorts = run_weekly(client, logger, today)
        else:
            content, path, longs, shorts = run_daily(client, logger, today)
    except PolygonAuthError as exc:
        logger.error(str(exc))
        raise SystemExit(1) from exc

    logger.info("Report saved to %s", path)
    logger.info("Long candidates: %d | Short candidates: %d", len(longs), len(shorts))
    print(content)


if __name__ == "__main__":
    main()
