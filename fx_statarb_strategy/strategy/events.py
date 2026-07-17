"""Event-driven blackout windows around high-impact USD/EUR/GBP macro
releases. Quantifiable and mechanical: a fixed window around each
scheduled release timestamp, not a discretionary "avoid news" rule."""

from __future__ import annotations

import datetime as dt
import json
from typing import List, Set

from fx_statarb_strategy import config


def load_events() -> List[dict]:
    with open(config.EVENTS_FILE) as fp:
        return json.load(fp)


def _parse(date_str: str) -> dt.datetime:
    return dt.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")


def blackout_bar_indices(
    bar_dates: List[str],
    events: List[dict] = None,
    minutes_before: int = None,
    minutes_after: int = None,
) -> Set[int]:
    """Returns the set of bar indices whose timestamp falls within
    [event_time - minutes_before, event_time + minutes_after] for any
    high-impact event. O(n_bars * n_events) -- fine at this data scale
    (a few thousand bars x ~130 events)."""
    events = events if events is not None else load_events()
    minutes_before = minutes_before if minutes_before is not None else config.EVENT_BLACKOUT_MINUTES_BEFORE
    minutes_after = minutes_after if minutes_after is not None else config.EVENT_BLACKOUT_MINUTES_AFTER

    event_times = [_parse(e["date"]) for e in events]
    before = dt.timedelta(minutes=minutes_before)
    after = dt.timedelta(minutes=minutes_after)

    blocked: Set[int] = set()
    for i, date_str in enumerate(bar_dates):
        bar_time = _parse(date_str)
        for et in event_times:
            if et - before <= bar_time <= et + after:
                blocked.add(i)
                break
    return blocked
