"""Python translation of the provided Pine Script v5 indicator
("Flagship: Velocity and Acceleration Signals") plus an EMA100 trend
filter and a volume-delta proxy. All functions operate on plain lists of
bars (dicts with open/high/low/close/volume) in ascending date order and
are strictly causal -- each index only ever looks at index <= i.
"""

from __future__ import annotations

from eurusd_strategy import config


def ema(values: list, length: int) -> list:
    """Standard exponential moving average. ta.ema seeds on the first
    value (Pine's ta.ema has no separate seed period, it starts EMA'ing
    from bar 1), so we do the same here for a faithful translation."""
    if not values:
        return []
    alpha = 2.0 / (length + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out


def velocity_series(closes: list, lookback: int = None) -> list:
    """velocitySum = sum_{i=1..lookback} (close - close[i]) / i; velocity =
    velocitySum / lookback. Bars before `lookback` history exists use as
    much history as is available (close[i] undefined -> treated as 0
    contribution), matching Pine's na-propagation-free na()-guarded
    behavior would differ, but since we only use these values after
    warmup for signals, the exact early-bar behavior is inconsequential."""
    lookback = lookback or config.VELOCITY_LOOKBACK
    n = len(closes)
    velocity = [0.0] * n
    for t in range(n):
        total = 0.0
        max_i = min(lookback, t)
        for i in range(1, max_i + 1):
            total += (closes[t] - closes[t - i]) / i
        velocity[t] = total / lookback if lookback else 0.0
    return velocity


def acceleration_series(velocity: list, lookback: int = None) -> list:
    """Same recurrence as velocity_series but applied to the velocity
    series itself, exactly mirroring the Pine Script's accelerationSum
    loop (which references `velocity`, the raw unsmoothed series, not
    smoothedVelocity)."""
    lookback = lookback or config.VELOCITY_LOOKBACK
    n = len(velocity)
    acceleration = [0.0] * n
    for t in range(n):
        total = 0.0
        max_i = min(lookback, t)
        for i in range(1, max_i + 1):
            total += (velocity[t] - velocity[t - i]) / i
        acceleration[t] = total / lookback if lookback else 0.0
    return acceleration


def crossover(series: list, threshold: float) -> list:
    """True at index t iff series[t-1] <= threshold < series[t] (Pine's
    ta.crossover semantics)."""
    n = len(series)
    out = [False] * n
    for t in range(1, n):
        if series[t - 1] <= threshold < series[t]:
            out[t] = True
    return out


def crossunder(series: list, threshold: float) -> list:
    n = len(series)
    out = [False] * n
    for t in range(1, n):
        if series[t - 1] >= threshold > series[t]:
            out[t] = True
    return out


def compute_velocity_acceleration(bars: list) -> dict:
    """Full translation of the Pine Script's core computation. Returns
    per-bar arrays aligned with `bars`: velocity, smoothed_velocity,
    acceleration, strong_up, strong_down."""
    closes = [b["close"] for b in bars]
    velocity = velocity_series(closes)
    smoothed_velocity = ema(velocity, config.VELOCITY_EMA_LENGTH)

    acceleration = acceleration_series(velocity)
    if config.SMOOTH_ACCELERATION:
        acceleration = ema(acceleration, config.ACCEL_EMA_LENGTH)

    up_cross = crossover(smoothed_velocity, config.VELOCITY_UP_THRESHOLD)
    down_cross = crossunder(smoothed_velocity, config.VELOCITY_DOWN_THRESHOLD)

    strong_up = [up_cross[t] and acceleration[t] > 0 for t in range(len(bars))]
    strong_down = [down_cross[t] and acceleration[t] < 0 for t in range(len(bars))]

    return {
        "velocity": velocity,
        "smoothed_velocity": smoothed_velocity,
        "acceleration": acceleration,
        "strong_up": strong_up,
        "strong_down": strong_down,
    }


def ema_trend_filter(bars: list, length: int = None) -> list:
    """EMA100 (or configured length) trend filter series."""
    length = length or config.EMA_TREND_LENGTH
    closes = [b["close"] for b in bars]
    return ema(closes, length)


def volume_delta_proxy(bars: list) -> list:
    """Chaikin-style close-location split of each bar's tick-count volume
    into an approximate buy/sell delta. NOT true order-flow: forex has no
    consolidated tape, and this feed's `volume` is a tick/update count.
    delta[t] = buy_volume[t] - sell_volume[t], where
    buy_volume = volume * (close-low)/(high-low),
    sell_volume = volume * (high-close)/(high-low).
    A doji bar (high == low) contributes zero delta rather than dividing
    by zero."""
    delta = []
    for b in bars:
        high, low, close, volume = b["high"], b["low"], b["close"], b["volume"]
        rng = high - low
        if rng <= 0:
            delta.append(0.0)
            continue
        buy_volume = volume * (close - low) / rng
        sell_volume = volume * (high - close) / rng
        delta.append(buy_volume - sell_volume)
    return delta
