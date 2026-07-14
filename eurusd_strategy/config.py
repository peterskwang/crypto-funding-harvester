"""Configuration for the EURUSD velocity/acceleration strategy."""

SYMBOL = "EURUSD"
DATA_FILE = "eurusd_strategy/data/eurusd_daily.json"

# -- TIMEFRAME --
# Daily bars, not intraday. Chosen deliberately: fetching a year+ of 1H/4H
# forex bars through this environment's MCP data relay risks the same
# context blowup that hit the pre-IPO project's multi-ticker daily-bar
# fetch. A single instrument's daily history (~2 years = ~586 bars) is
# within the range already proven safe there. This also matches the
# indicator's own defaults (14-period lookback, 20-period EMA smoothing)
# reasonably well -- those read as swing-style parameters, not scalping
# ones. Tradeoff: this strategy is a daily-bar swing system, not the
# intraday system the original Pine Script is sometimes used for.

# -- VELOCITY / ACCELERATION (translated 1:1 from the provided Pine Script) --
VELOCITY_LOOKBACK = 14        # Pine `lookback`
VELOCITY_EMA_LENGTH = 20      # Pine `emaLength` (smooths velocity)
ACCEL_EMA_LENGTH = 5          # Pine `emaLength2` (smooths acceleration, if enabled)
SMOOTH_ACCELERATION = False   # Pine `smoothAccel` default

# Pine's default thresholds (0.01 / -0.01) are calibrated for stocks priced
# in tens/hundreds of dollars, where close-to-close deltas are ~0.1-1.0.
# EURUSD trades ~1.0-1.2 with daily closes typically ~0.001-0.01 apart, so
# the raw velocity/acceleration units are roughly two orders of magnitude
# smaller. Reusing 0.01 verbatim would mean the signal almost never fires.
# This is a one-time *unit* recalibration (matching the threshold to the
# instrument's price scale): computed as ~1 standard deviation (~0.00088,
# rounded to 0.0009) of the post-warmup smoothedVelocity series over the
# full 2024-07-15..2026-07-14 daily data window. Derived once from the
# series' own statistics, NOT by trying values until backtest P&L looked
# good -- see calibrate.py for the exact derivation and how to re-run it.
# (0.00088, from calibrate.py's output as of the 586-bar 2024-2026 window.)
VELOCITY_UP_THRESHOLD = 0.00088
VELOCITY_DOWN_THRESHOLD = -0.00088

# -- TREND FILTER --
EMA_TREND_LENGTH = 100   # only take longs above EMA100, shorts below EMA100

# -- VOLUME DELTA PROXY --
# Forex is OTC/decentralized -- there is no consolidated tape, so "volume"
# in this feed is a tick/update count, not executed size, and there is no
# real aggressor (buy vs. sell) delta available. This proxies delta from
# each bar's OHLC using the standard Chaikin-style intrabar close-location
# split: buy_volume = volume * (close-low)/(high-low), sell_volume the
# complement. This is a well-known approximation, not order-flow truth --
# disclosed here and in the report, same as every other proxy in this repo.
VOLUME_DELTA_CONFIRM = True   # require delta to agree with signal direction

# -- BACKTEST --
TRAILING_STOP_PCT = 0.02   # 2%: computed from this dataset's own daily range
                            # (mean high-low range 0.63% of close, mean abs
                            # close-to-close move 0.32%), sized to roughly 3x
                            # the average daily range so it survives normal
                            # noise but still cuts a real reversal. A 10%
                            # equity-style stop (as used for IPO stocks in
                            # pre_ipo_screener) would almost never trigger on
                            # an instrument this much less volatile than a
                            # newly-listed stock. Sized to actual volatility,
                            # not fit to backtest P&L -- see the backtest
                            # report for the honest caveat that at this width
                            # the stop rarely binds before MAX_HOLD_DAYS, so
                            # in practice most trades are closer to a fixed
                            # 20-day hold with a disaster-stop safety net.
MAX_HOLD_DAYS = 20          # cap a trade at ~1 trading month regardless of trail
INITIAL_CAPITAL = 10_000.0  # notional, for equity-curve reporting only

BACKTEST_REPORTS_DIR = "eurusd_strategy/reports"
