"""Renders the dated markdown report of long/short picks and pattern references."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional

from pre_ipo_screener import config

DISCLAIMER = (
    "> **Not investment advice.** This is an automated, rules-based research tool. "
    "It scores candidates using public IPO calendar data and historical price patterns; "
    "it does not account for fundamentals, news, or market regime shifts. Verify "
    "everything independently before risking capital."
)


def _fmt_pct(value: Optional[float]) -> str:
    return f"{value:+.1%}" if value is not None else "n/a"


def _fmt_money(value: Optional[float]) -> str:
    return f"${value:,.0f}" if value is not None else "n/a"


def _long_table(candidates: List[Dict[str, Any]]) -> str:
    if not candidates:
        return "_No long candidates cleared the score threshold this run._\n"
    lines = ["| Ticker | Company | Listing Date | Score | Deal Size | Rationale |", "|---|---|---|---|---|---|"]
    for c in candidates:
        rationale = "<br>".join(c.get("rationale", []))
        lines.append(
            f"| **{c['ticker']}** | {c['name']} | {c['listing_date']} | {c['score']} | "
            f"{_fmt_money(c.get('total_offer_size'))} | {rationale} |"
        )
    return "\n".join(lines) + "\n"


def _short_table(candidates: List[Dict[str, Any]]) -> str:
    if not candidates:
        return "_No short/fade candidates flagged this run._\n"
    lines = ["| Ticker | Company | Listing Date | Conviction | Reasons | Suggested Style |", "|---|---|---|---|---|---|"]
    for c in candidates:
        lines.append(
            f"| **{c['ticker']}** | {c['name']} | {c['listing_date']} | {c['conviction']} | "
            f"{', '.join(c.get('reasons', []))} | {c.get('suggested_style', '')} |"
        )
    return "\n".join(lines) + "\n"


def _analog_table(analog_groups: Dict[str, Dict[str, Any]]) -> str:
    if not analog_groups:
        return "_No historical analog groups available this run._\n"
    lines = ["| Sector | Deal Tier | Count | Avg Week-1 Return | Avg Month-1 Return | Tickers |", "|---|---|---|---|---|---|"]
    for group in sorted(analog_groups.values(), key=lambda g: g["avg_week1_return"], reverse=True):
        lines.append(
            f"| {group['sector']} | {group['tier']} | {group['count']} | "
            f"{_fmt_pct(group['avg_week1_return'])} | {_fmt_pct(group['avg_month1_return'])} | "
            f"{', '.join(group['tickers'])} |"
        )
    return "\n".join(lines) + "\n"


def render_report(
    long_candidates: List[Dict[str, Any]],
    short_candidates: List[Dict[str, Any]],
    analog_groups: Dict[str, Dict[str, Any]],
    run_date: Optional[dt.date] = None,
    mode: str = "weekly",
) -> str:
    run_date = run_date or dt.date.today()
    sections = [
        f"# Pre-IPO Screener Report — {run_date.isoformat()} ({mode})",
        "",
        DISCLAIMER,
        "",
        "## Top Long Candidates (upcoming IPOs)",
        _long_table(long_candidates),
        "## Top Short / Fade Candidates (recent IPOs)",
        _short_table(short_candidates),
        "## Historical Pattern Reference (last ~120 days)",
        _analog_table(analog_groups),
    ]
    return "\n".join(sections)


def save_report(content: str, run_date: Optional[dt.date] = None, reports_dir: Optional[str] = None) -> str:
    run_date = run_date or dt.date.today()
    reports_dir = reports_dir or config.REPORTS_DIR
    path = Path(reports_dir) / f"{run_date.isoformat()}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path)
