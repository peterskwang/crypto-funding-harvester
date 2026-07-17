from fx_statarb_strategy.strategy import bars


def _bar(date, o, h, l, c, v):
    return {"date": date, "open": o, "high": h, "low": l, "close": c, "volume": v}


def test_aggregate_15m_groups_three_5min_bars():
    raw = [
        _bar("2026-01-05 09:00:00", 1.10, 1.11, 1.09, 1.105, 100),
        _bar("2026-01-05 09:05:00", 1.105, 1.12, 1.10, 1.115, 150),
        _bar("2026-01-05 09:10:00", 1.115, 1.13, 1.11, 1.12, 120),
        _bar("2026-01-05 09:15:00", 1.12, 1.14, 1.115, 1.13, 90),
    ]
    out = bars.aggregate_15m(raw)
    assert len(out) == 2
    first = out[0]
    assert first["date"] == "2026-01-05 09:00:00"
    assert first["open"] == 1.10
    assert first["close"] == 1.12
    assert first["high"] == 1.13
    assert first["low"] == 1.09
    assert first["volume"] == 370
    assert first["n_5m_bars"] == 3

    second = out[1]
    assert second["date"] == "2026-01-05 09:15:00"
    assert second["n_5m_bars"] == 1


def test_aggregate_15m_bucket_boundaries():
    # minutes 20, 25, 29 should NOT bucket with minute 30 -- 15/20/25 is one
    # bucket (floor(20/15)*15=15), 30 starts a fresh one.
    raw = [
        _bar("2026-01-05 09:16:00", 1.0, 1.0, 1.0, 1.0, 1),
        _bar("2026-01-05 09:29:00", 1.0, 1.0, 1.0, 1.0, 1),
        _bar("2026-01-05 09:30:00", 1.0, 1.0, 1.0, 1.0, 1),
    ]
    out = bars.aggregate_15m(raw)
    assert len(out) == 2
    assert out[0]["date"] == "2026-01-05 09:15:00"
    assert out[0]["n_5m_bars"] == 2
    assert out[1]["date"] == "2026-01-05 09:30:00"
    assert out[1]["n_5m_bars"] == 1


def test_align_inner_joins_on_date():
    a = [_bar("2026-01-05 09:00:00", 1, 1, 1, 1, 1), _bar("2026-01-05 09:15:00", 1, 1, 1, 1, 1)]
    b = [_bar("2026-01-05 09:15:00", 2, 2, 2, 2, 2), _bar("2026-01-05 09:30:00", 2, 2, 2, 2, 2)]
    aligned_a, aligned_b = bars.align(a, b)
    assert len(aligned_a) == 1
    assert aligned_a[0]["date"] == "2026-01-05 09:15:00"
    assert aligned_b[0]["date"] == "2026-01-05 09:15:00"
