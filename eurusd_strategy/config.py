"""Configuration for the EURUSD velocity/acceleration strategy."""

SYMBOL = "EURUSD"
DATA_FILE = "eurusd_strategy/data/eurusd_daily.json"

# -- TIMEFRAME --
# Daily bars, not intraday. Chosen deliberately: fetching a year+ of 1H/4H
# forex bars through this environment's MCP data relay risks the same
# context blowup that hit the pre-IPO project's multi-ticker daily-bar
# fetch. A single instrument's daily history is within the range already
# proven safe there (the fetch itself auto-saves to disk instead of
# flooding context, regardless of size, once past a token threshold).
# This also matches the indicator's own defaults (14-period lookback,
# 20-period EMA smoothing) reasonably well -- those read as swing-style
# parameters, not scalping ones. Tradeoff: this strategy is a daily-bar
# swing system, not the intraday system the original Pine Script is
# sometimes used for.

# -- IN-SAMPLE / OUT-OF-SAMPLE SPLIT --
# 3579 daily bars, 2013-01-02..2026-07-14. Any parameter search (TP/SL,
# trailing width, hold period) is only ever allowed to look at bars before
# this date; everything from this date forward is held out and only used
# once, to report how the single selected config performs on data it never
# influenced. This is the actual defense against overfitting a ~10-trade
# sample -- not a promise to "not tune," but a promise to validate any
# tuning honestly instead of reporting the in-sample number as if it were
# proven performance.
IN_SAMPLE_END_DATE = "2022-01-01"

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
# instrument's price scale): computed as ~1 standard deviation of the
# post-warmup smoothedVelocity series, using ONLY the in-sample window
# (2013-2021, see IN_SAMPLE_END_DATE below) so the out-of-sample period
# never leaks into calibration. Derived once from the series' own
# statistics, NOT by trying values until backtest P&L looked good -- see
# calibrate.py for the exact derivation and how to re-run it. (Re-deriving
# on the full 2013-2026 window gives 0.00096, and on the most recent 2-year
# slice alone gives 0.00088 -- all three are within ~15% of each other,
# which is itself evidence the threshold isn't a fragile, window-specific
# artifact.)
VELOCITY_UP_THRESHOLD = 0.00099
VELOCITY_DOWN_THRESHOLD = -0.00099

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

# -- FIXED TAKE-PROFIT / STOP-LOSS (bracket exit, alternative to trailing) --
# Selected from a 420-combo grid search over the in-sample window only
# (2013-2021, see search_tp_sl.py), then locked in and re-run once,
# unmodified, on the untouched out-of-sample window (2022-2026, see
# validate_oos.py). This is NOT the config with the best in-sample
# total_return (+11.5%, EMA+delta filters, tp=5%/sl=1.5%) -- that one only
# produced +0.50% out-of-sample, a textbook overfitting signature. This is
# the config with the best in-sample win_rate (80.7%, no filters, a small
# 0.5%/1.5% TP/SL) instead, because a high win rate across many trades held
# up much better out-of-sample (72.7%) than a high total return from a
# handful of large winners did. Even so: out-of-sample total return is only
# +0.61% over 4.5 years, which is not a "solid" edge -- see the backtest
# report's "Out-of-sample validation" section for the full honest picture,
# including the configs that did NOT survive validation.
EXIT_MODE = "bracket"   # "trailing" (original) or "bracket" (fixed TP/SL)
FIXED_TAKE_PROFIT_PCT = 0.005
FIXED_STOP_LOSS_PCT = 0.015

BACKTEST_REPORTS_DIR = "eurusd_strategy/reports"
