"""One-time derivation of VELOCITY_UP_THRESHOLD / VELOCITY_DOWN_THRESHOLD in
config.py. Run this manually (`python -m eurusd_strategy.calibrate`) if the
data window changes and the thresholds need re-deriving -- it is NOT part of
the backtest run loop, and re-running it after seeing backtest results in
order to pick a more "favorable" threshold would defeat its purpose.

Method: threshold = 1 standard deviation of the post-warmup smoothedVelocity
series. This targets "a meaningfully large move relative to this
instrument's own recent behavior," which is the same intent as the Pine
Script's fixed 0.01 default for stock-scale prices -- just re-expressed in
EURUSD's own units instead of copying a number calibrated for a different
instrument. It is computed once from the series' statistics, before any
backtest is run, so it cannot be back-fit to trade outcomes.
"""

import json

from eurusd_strategy import config
from eurusd_strategy.strategy import indicators

WARMUP_BARS = config.VELOCITY_LOOKBACK + config.VELOCITY_EMA_LENGTH + 6


def derive_thresholds(bars: list) -> tuple:
    closes = [b["close"] for b in bars]
    velocity = indicators.velocity_series(closes)
    smoothed = indicators.ema(velocity, config.VELOCITY_EMA_LENGTH)
    sample = smoothed[WARMUP_BARS:]

    mean = sum(sample) / len(sample)
    variance = sum((x - mean) ** 2 for x in sample) / len(sample)
    std = variance ** 0.5
    return round(std, 5), round(-std, 5)


if __name__ == "__main__":
    with open(config.DATA_FILE) as fp:
        bars = json.load(fp)
    up, down = derive_thresholds(bars)
    print(f"n bars: {len(bars)}, post-warmup sample: {len(bars) - WARMUP_BARS}")
    print(f"derived VELOCITY_UP_THRESHOLD = {up}")
    print(f"derived VELOCITY_DOWN_THRESHOLD = {down}")
