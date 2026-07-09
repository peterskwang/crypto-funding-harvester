import datetime as dt

from pre_ipo_screener.screener.backtest import summarize_trades
from pre_ipo_screener.screener.report import (
    render_backtest_report,
    render_report,
    save_backtest_report,
    save_report,
)

RUN_DATE = dt.date(2026, 7, 9)

LONG_CANDIDATES = [
    {
        "ticker": "ACRB",
        "name": "Acme Robotics Inc.",
        "listing_date": "2026-07-16",
        "score": 88.6,
        "total_offer_size": 500_000_000,
        "rationale": ["Deal size tier: mid", "Analog group TECH/mid averaged +12.0% in week 1"],
    }
]

SHORT_CANDIDATES = [
    {
        "ticker": "HOTX",
        "name": "Hot Co",
        "listing_date": "2026-06-29",
        "conviction": 71.0,
        "reasons": ["momentum_fade"],
        "suggested_style": "Day 1-2 momentum trade (high volatility, short hold)",
    }
]

ANALOG_GROUPS = {
    "TECH|mid": {
        "sector": "TECH",
        "tier": "mid",
        "count": 5,
        "avg_week1_return": 0.12,
        "avg_month1_return": 0.08,
        "tickers": ["A", "B"],
    }
}


def test_render_report_includes_disclaimer_and_candidates():
    content = render_report(LONG_CANDIDATES, SHORT_CANDIDATES, ANALOG_GROUPS, RUN_DATE, mode="weekly")

    assert "Not investment advice" in content
    assert "ACRB" in content
    assert "HOTX" in content
    assert "TECH" in content
    assert "2026-07-09" in content


def test_render_report_handles_empty_buckets():
    content = render_report([], [], {}, RUN_DATE, mode="daily")

    assert "No long candidates" in content
    assert "No short/fade candidates" in content
    assert "No historical analog groups" in content


def test_save_report_writes_file(tmp_path):
    content = render_report(LONG_CANDIDATES, SHORT_CANDIDATES, ANALOG_GROUPS, RUN_DATE)

    path = save_report(content, RUN_DATE, reports_dir=str(tmp_path))

    saved = tmp_path / "2026-07-09.md"
    assert saved.exists()
    assert saved.read_text(encoding="utf-8") == content
    assert path == str(saved)


BACKTEST_TRADES = [
    {
        "ticker": "ACRB", "name": "Acme Robotics", "direction": "LONG", "style": "2-4 week swing hold",
        "entry_date": "2026-01-02", "entry_price": 10.0, "exit_date": "2026-01-23", "exit_price": 11.5,
        "holding_days": 15, "return_pct": 0.15,
    },
    {
        "ticker": "HOTX", "name": "Hot Co", "direction": "SHORT", "style": "Momentum fade",
        "entry_date": "2026-02-01", "entry_price": 20.0, "exit_date": "2026-02-15", "exit_price": 16.0,
        "holding_days": 10, "return_pct": 0.20,
    },
]


def test_render_backtest_report_includes_trades_and_summary():
    summary = summarize_trades(BACKTEST_TRADES)

    content = render_backtest_report(BACKTEST_TRADES, summary, dt.date(2026, 1, 1), dt.date(2026, 3, 1), data_source="Polygon.io (live)")

    assert "Not investment advice" in content
    assert "Polygon.io (live)" in content
    assert "ACRB" in content
    assert "HOTX" in content
    assert "Overall" in content
    assert "Best trade" in content


def test_render_backtest_report_handles_no_trades():
    summary = summarize_trades([])

    content = render_backtest_report([], summary, dt.date(2026, 1, 1), dt.date(2026, 3, 1), data_source="synthetic (test)")

    assert "No trades triggered" in content


def test_save_backtest_report_writes_file(tmp_path):
    summary = summarize_trades(BACKTEST_TRADES)
    content = render_backtest_report(BACKTEST_TRADES, summary, dt.date(2026, 1, 1), dt.date(2026, 3, 1), data_source="Polygon.io (live)")

    path = save_backtest_report(content, dt.date(2026, 1, 1), dt.date(2026, 3, 1), reports_dir=str(tmp_path))

    saved = tmp_path / "2026-01-01_to_2026-03-01.md"
    assert saved.exists()
    assert path == str(saved)
