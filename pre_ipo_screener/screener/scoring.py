"""Composite scoring for upcoming (long) candidates and fade/lockup (short) candidates.

This is a transparent, rules-based heuristic model — not a trained predictor.
Every weight lives in config.py so the methodology can be inspected and tuned.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from pre_ipo_screener import config
from pre_ipo_screener.screener.historical import deal_size_tier

# Deal-size heuristic: small/mid-cap IPOs have historically shown larger
# first-week pops than mega-deals, which tend to already be priced efficiently
# by institutional demand. This is a starting assumption, tune as data comes in.
DEAL_SIZE_BASELINE_SCORE = {
    "micro": 60.0,
    "small": 80.0,
    "mid": 70.0,
    "large": 55.0,
    "unknown": 40.0,
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _analog_score(candidate: Dict[str, Any], analog_groups: Dict[str, Dict[str, Any]]) -> "tuple[float, Optional[Dict[str, Any]]]":
    sector = candidate.get("sector_tag", "OTHER")
    tier = deal_size_tier(candidate.get("total_offer_size"))
    group = analog_groups.get(f"{sector}|{tier}")
    if not group:
        return 50.0, None
    avg_return = group["avg_week1_return"]
    return _clamp(50 + avg_return * 500), group


def _proximity_score(candidate: Dict[str, Any], today: dt.date) -> float:
    try:
        listing_date = dt.date.fromisoformat(candidate["listing_date"])
    except (KeyError, ValueError):
        return 50.0
    days_to_listing = (listing_date - today).days
    if days_to_listing < 0:
        return 50.0
    return _clamp(100 - (days_to_listing / max(config.LOOKAHEAD_DAYS, 1)) * 100)


def score_upcoming(
    candidate: Dict[str, Any],
    analog_groups: Dict[str, Dict[str, Any]],
    today: Optional[dt.date] = None,
) -> Dict[str, Any]:
    """Scores a single upcoming IPO candidate 0-100 and assigns LONG/WATCH direction."""
    today = today or dt.date.today()
    tier = deal_size_tier(candidate.get("total_offer_size"))
    deal_score = DEAL_SIZE_BASELINE_SCORE.get(tier, 40.0)
    analog_score, matched_group = _analog_score(candidate, analog_groups)
    proximity_score = _proximity_score(candidate, today)

    composite = (
        deal_score * config.SCORE_WEIGHT_DEAL_SIZE
        + analog_score * config.SCORE_WEIGHT_ANALOG_RETURN
        + proximity_score * config.SCORE_WEIGHT_PROXIMITY
    )
    direction = "LONG" if composite >= config.LONG_SCORE_WATCH_THRESHOLD else "WATCH"

    rationale = [f"Deal size tier: {tier} (offer size ${candidate.get('total_offer_size') or 0:,.0f})"]
    if matched_group:
        rationale.append(
            f"Analog group {matched_group['sector']}/{matched_group['tier']} "
            f"(n={matched_group['count']}) averaged {matched_group['avg_week1_return']:+.1%} in week 1"
        )
    else:
        rationale.append("No historical analog group match — neutral weighting applied")
    rationale.append(f"Listing date {candidate['listing_date']} ({candidate.get('exchange') or 'unknown exchange'})")

    result = dict(candidate)
    result.update(
        {
            "score": round(composite, 1),
            "direction": direction,
            "rationale": rationale,
        }
    )
    return result


def score_fade_candidates(recent_candidates_with_perf: List[Dict[str, Any]], today: Optional[dt.date] = None) -> List[Dict[str, Any]]:
    """Flags recent IPOs as short candidates: momentum fades and lockup-expiry watches."""
    today = today or dt.date.today()
    flagged: List[Dict[str, Any]] = []

    for candidate in recent_candidates_with_perf:
        day1_pop = candidate.get("day1_pop")
        decay_from_high = candidate.get("decay_from_high")
        listing_date = candidate.get("listing_date")

        reasons: List[str] = []
        conviction = 0.0

        if (
            day1_pop is not None
            and day1_pop >= config.FADE_DAY1_POP_THRESHOLD
            and decay_from_high is not None
            and decay_from_high <= config.FADE_DECAY_THRESHOLD
        ):
            reasons.append("momentum_fade")
            conviction = max(conviction, _clamp(50 + abs(decay_from_high) * 300))

        try:
            days_since_listing = (today - dt.date.fromisoformat(listing_date)).days if listing_date else None
        except ValueError:
            days_since_listing = None

        lo, hi = config.LOCKUP_WINDOW_DAYS
        if days_since_listing is not None and lo <= days_since_listing <= hi:
            reasons.append("lockup_expiry_watch")
            conviction = max(conviction, 55.0)

        if not reasons:
            continue

        result = dict(candidate)
        result.update(
            {
                "direction": "SHORT",
                "reasons": reasons,
                "conviction": round(conviction, 1),
                "days_since_listing": days_since_listing,
            }
        )
        flagged.append(result)

    return flagged


def suggested_style(candidate: Dict[str, Any]) -> str:
    """Maps realized volatility / signal type to a suggested holding style."""
    if "lockup_expiry_watch" in (candidate.get("reasons") or []):
        return "Lockup-expiry short watch (~90-180d post-listing)"

    volatility = candidate.get("realized_volatility")
    if volatility is None:
        return "Insufficient trading history — monitor"
    if volatility >= config.HIGH_VOLATILITY_CUTOFF:
        return "Day 1-2 momentum trade (high volatility, short hold)"
    if volatility >= config.MODERATE_VOLATILITY_CUTOFF:
        return "2-4 week swing hold"
    return "Position hold (low volatility, longer horizon)"


def rank_candidates(scored: List[Dict[str, Any]], key: str, top_n: Optional[int] = None) -> List[Dict[str, Any]]:
    top_n = top_n or config.TOP_N_PER_BUCKET
    ranked = sorted(scored, key=lambda c: c.get(key, 0), reverse=True)
    return ranked[:top_n]
