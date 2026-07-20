import pytest

from ml_entry_strategy.strategy import bars


def _bar(date, o, h, l, c, v):
    return {"date": date, "open": o, "high": h, "low": l, "close": c, "volume": v}


def test_clean_volume_outliers_repairs_flagged_bar_only():
    raw = [
        _bar("2026-01-01 00:00:00", 100, 101, 99, 100, 1_000_000),
        _bar("2026-01-01 00:05:00", 100, 101, 99, 100, 1_200_000),
        _bar("2026-01-01 00:10:00", 100, 101, 99, 100, 20_000_000_000),  # glitch
        _bar("2026-01-01 00:15:00", 100, 101, 99, 100, 900_000),
        _bar("2026-01-01 00:20:00", 100, 101, 99, 100, 1_100_000),
    ]
    cleaned = bars.clean_volume_outliers(raw)

    assert cleaned[2]["volume"] < bars.VOLUME_OUTLIER_THRESHOLD
    assert cleaned[2]["volume_glitch_repaired"] is True
    # OHLC untouched
    for orig, fixed in zip(raw, cleaned):
        assert fixed["open"] == orig["open"]
        assert fixed["high"] == orig["high"]
        assert fixed["low"] == orig["low"]
        assert fixed["close"] == orig["close"]
    # non-flagged bars pass through with volume unchanged
    for i in (0, 1, 3, 4):
        assert cleaned[i]["volume"] == raw[i]["volume"]
        assert "volume_glitch_repaired" not in cleaned[i]


def test_clean_volume_outliers_no_flags_is_noop():
    raw = [
        _bar("2026-01-01 00:00:00", 100, 101, 99, 100, 1_000_000),
        _bar("2026-01-01 00:05:00", 100, 101, 99, 100, 1_200_000),
    ]
    cleaned = bars.clean_volume_outliers(raw)
    assert cleaned == raw


def test_aggregate_15m_groups_three_5m_bars_correctly():
    raw = [
        _bar("2026-01-01 00:00:00", 100, 105, 98, 102, 10),
        _bar("2026-01-01 00:05:00", 102, 106, 101, 104, 20),
        _bar("2026-01-01 00:10:00", 104, 107, 103, 103, 30),
        _bar("2026-01-01 00:15:00", 103, 108, 102, 106, 5),
    ]
    out = bars.aggregate_15m(raw)
    assert len(out) == 2
    first = out[0]
    assert first["date"] == "2026-01-01 00:00:00"
    assert first["open"] == 100
    assert first["high"] == 107
    assert first["low"] == 98
    assert first["close"] == 103
    assert first["volume"] == 60
    assert first["n_5m_bars"] == 3

    second = out[1]
    assert second["date"] == "2026-01-01 00:15:00"
    assert second["n_5m_bars"] == 1
