import pytest

from ml_entry_strategy import config
from ml_entry_strategy.strategy import labels


@pytest.fixture(autouse=True)
def small_config(monkeypatch):
    """Small, deterministic barrier config so synthetic fixtures stay tiny."""
    monkeypatch.setattr(config, "ATR_LOOKBACK", 3)
    monkeypatch.setattr(config, "PROFIT_TARGET_ATR_MULT", 1.5)
    monkeypatch.setattr(config, "STOP_LOSS_ATR_MULT", 1.0)
    monkeypatch.setattr(config, "MAX_HOLD_BARS", 5)


def _flat_bar(c):
    """A bar with true range 2.0 relative to a same-close neighbor."""
    return {"open": c, "high": c + 1, "low": c - 1, "close": c}


def _move_bar(open_, high, low, close):
    return {"open": open_, "high": high, "low": low, "close": close}


def _warmup(c=100.0, n=6):
    return [_flat_bar(c) for _ in range(n)]


def test_long_hits_profit_target_first():
    bars = _warmup() + [_move_bar(100, 103.5, 99.5, 103)] + [_flat_bar(100)] * 5
    t = 5  # last warmup bar, entry_price=100, ATR=2 -> profit=103, stop=98
    result = labels._label_one(bars, t, atr=2.0, direction="long")
    assert result["label"] == 1
    assert result["exit_reason"] == "profit"
    assert result["bars_held"] == 1
    assert result["realized_return"] == pytest.approx(0.03)


def test_long_hits_stop_loss_first():
    bars = _warmup() + [_move_bar(100, 100.5, 97.5, 98)] + [_flat_bar(100)] * 5
    t = 5
    result = labels._label_one(bars, t, atr=2.0, direction="long")
    assert result["label"] == 0
    assert result["exit_reason"] == "stop"
    assert result["bars_held"] == 1
    assert result["realized_return"] == pytest.approx(-0.02)


def test_long_time_barrier_expires_without_touch():
    bars = _warmup() + [_flat_bar(100)] * 5  # never leaves [99, 101], barriers are 98/103
    t = 5
    result = labels._label_one(bars, t, atr=2.0, direction="long")
    assert result["label"] == 0
    assert result["exit_reason"] == "time"
    assert result["bars_held"] == config.MAX_HOLD_BARS


def test_short_hits_profit_target_first():
    # short profit = entry - 1.5*ATR = 97, stop = entry + 1.0*ATR = 102
    bars = _warmup() + [_move_bar(100, 100.5, 96.5, 97)] + [_flat_bar(100)] * 5
    t = 5
    result = labels._label_one(bars, t, atr=2.0, direction="short")
    assert result["label"] == 1
    assert result["exit_reason"] == "profit"
    assert result["realized_return"] == pytest.approx(0.03)


def test_short_hits_stop_first():
    bars = _warmup() + [_move_bar(100, 102.5, 99.5, 102)] + [_flat_bar(100)] * 5
    t = 5
    result = labels._label_one(bars, t, atr=2.0, direction="short")
    assert result["label"] == 0
    assert result["exit_reason"] == "stop"
    assert result["realized_return"] == pytest.approx(-0.02)


def test_same_bar_ambiguous_resolves_toward_open_proximity():
    # single forward bar spans both barriers (98 and 103); open near stop -> stop wins
    bars = _warmup() + [_move_bar(open_=98.5, high=103.5, low=97.5, close=100)] + [_flat_bar(100)] * 5
    t = 5
    result = labels._label_one(bars, t, atr=2.0, direction="long")
    assert result["exit_reason"] == "stop"

    # same bar shape, but open near profit -> profit wins
    bars2 = _warmup() + [_move_bar(open_=102.5, high=103.5, low=97.5, close=100)] + [_flat_bar(100)] * 5
    result2 = labels._label_one(bars2, t, atr=2.0, direction="long")
    assert result2["exit_reason"] == "profit"


def test_not_enough_forward_bars_returns_none():
    bars = _warmup()  # only warmup bars, no room for MAX_HOLD_BARS forward
    t = len(bars) - 1
    result = labels._label_one(bars, t, atr=2.0, direction="long")
    assert result is None


def test_label_bars_none_during_atr_warmup_and_end_of_series():
    bars = _warmup(n=20)
    out = labels.label_bars(bars, "long")
    assert len(out) == len(bars)
    assert out[0] is None  # true_range/ATR warm-up
    # last MAX_HOLD_BARS entries can't resolve (no forward data)
    for t in range(len(bars) - config.MAX_HOLD_BARS, len(bars)):
        assert out[t] is None
