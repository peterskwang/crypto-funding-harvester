import datetime as dt

from pre_ipo_screener.screener.historical import deal_size_tier
from pre_ipo_screener.screener.scoring import (
    rank_candidates,
    score_fade_candidates,
    score_upcoming,
    suggested_style,
)

TODAY = dt.date(2026, 7, 9)


def test_deal_size_tier_boundaries():
    assert deal_size_tier(50_000_000) == "micro"
    assert deal_size_tier(75_000_000) == "small"
    assert deal_size_tier(1_000_000_000) == "large"
    assert deal_size_tier(None) == "unknown"


def test_score_upcoming_strong_analog_match_yields_long():
    candidate = {
        "ticker": "ACRB",
        "name": "Acme Robotics Inc.",
        "listing_date": "2026-07-16",
        "exchange": "XNAS",
        "total_offer_size": 500_000_000,
        "sector_tag": "TECH",
    }
    analog_groups = {
        "TECH|mid": {
            "sector": "TECH",
            "tier": "mid",
            "count": 5,
            "avg_week1_return": 0.12,
            "avg_month1_return": 0.08,
            "tickers": ["A", "B"],
        }
    }

    result = score_upcoming(candidate, analog_groups, today=TODAY)

    assert result["direction"] == "LONG"
    assert result["score"] > 55
    assert any("analog group" in r.lower() for r in result["rationale"])


def test_score_upcoming_no_analog_and_far_listing_yields_watch():
    candidate = {
        "ticker": "MYST",
        "name": "Mystery Co.",
        "listing_date": "2026-08-18",  # 40 days out
        "exchange": "XNYS",
        "total_offer_size": None,
        "sector_tag": "OTHER",
    }

    result = score_upcoming(candidate, analog_groups={}, today=TODAY)

    assert result["direction"] == "WATCH"
    assert result["score"] < 55


def test_score_fade_candidates_flags_momentum_fade_and_lockup_watch():
    fade_candidate = {
        "ticker": "HOTX",
        "name": "Hot Co",
        "listing_date": (TODAY - dt.timedelta(days=10)).isoformat(),
        "day1_pop": 0.25,
        "decay_from_high": -0.12,
        "realized_volatility": 0.08,
    }
    lockup_candidate = {
        "ticker": "LOCK",
        "name": "Lockup Co",
        "listing_date": (TODAY - dt.timedelta(days=120)).isoformat(),
        "day1_pop": 0.02,
        "decay_from_high": -0.01,
        "realized_volatility": 0.02,
    }
    quiet_candidate = {
        "ticker": "QUIET",
        "name": "Quiet Co",
        "listing_date": (TODAY - dt.timedelta(days=10)).isoformat(),
        "day1_pop": 0.02,
        "decay_from_high": -0.01,
        "realized_volatility": 0.01,
    }

    flagged = score_fade_candidates([fade_candidate, lockup_candidate, quiet_candidate], today=TODAY)
    flagged_by_ticker = {f["ticker"]: f for f in flagged}

    assert set(flagged_by_ticker) == {"HOTX", "LOCK"}
    assert "momentum_fade" in flagged_by_ticker["HOTX"]["reasons"]
    assert "lockup_expiry_watch" in flagged_by_ticker["LOCK"]["reasons"]


def test_suggested_style_prioritizes_lockup_reason():
    assert "Lockup-expiry" in suggested_style({"reasons": ["lockup_expiry_watch"], "realized_volatility": 0.02})


def test_suggested_style_uses_volatility_cutoffs():
    assert "Day 1-2" in suggested_style({"reasons": [], "realized_volatility": 0.08})
    assert "swing hold" in suggested_style({"reasons": [], "realized_volatility": 0.04})
    assert "Insufficient" in suggested_style({"reasons": [], "realized_volatility": None})


def test_rank_candidates_sorts_and_truncates():
    candidates = [{"ticker": "A", "score": 10}, {"ticker": "B", "score": 90}, {"ticker": "C", "score": 50}]

    ranked = rank_candidates(candidates, key="score", top_n=2)

    assert [c["ticker"] for c in ranked] == ["B", "C"]
