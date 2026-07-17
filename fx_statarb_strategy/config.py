"""Configuration for the EURUSD/GBPUSD statistical-arbitrage pairs strategy.

Core idea (the "Simons-style" piece the user asked for): don't predict the
direction of either pair individually. Instead trade the SPREAD between
them -- EURUSD and GBPUSD are structurally correlated (both USD-legs,
overlapping European economics/rate cycles) with a correlation typically
above 0.8 on this window (see calibrate.py for the measured value). When
the spread statistically diverges from its normal relationship, bet on
reversion; when the relationship itself looks unstable (regime breakdown,
e.g. around ECB/BoE policy divergence), stand aside instead of forcing a
trade. This is a real quantitative concept (pairs trading / stat-arb), not
a technical indicator wearing a disguise.

Versions v1.0-v5.0 live in strategy/backtest.py as named parameter presets
that each fix one concrete flaw found in the previous version -- see that
file's module docstring for the changelog.
"""

SYMBOLS = ("EURUSD", "GBPUSD")
DATA_FILES = {
    "EURUSD": "fx_statarb_strategy/data/eurusd_5m.json",
    "GBPUSD": "fx_statarb_strategy/data/gbpusd_5m.json",
}

# -- TIMEFRAMES --
# FMP's forex intraday API only offers 1/5/60-minute bars (no native 15-min),
# so 15-min bars are built by aggregating three consecutive 5-min bars in
# bars.py. Signal generation runs on the 15-min series (per the user's
# request); entries are timed to 1-min bars in v4.0+ once the signal fires.
BASE_TIMEFRAME_MINUTES = 5
SIGNAL_TIMEFRAME_MINUTES = 15
AGG_FACTOR = SIGNAL_TIMEFRAME_MINUTES // BASE_TIMEFRAME_MINUTES

# -- DATA WINDOW --
# ~89 days of 5-min bars (2026-04-19 to 2026-07-16), fetched in 10-day
# chunks (the API caps each call at roughly that range regardless of the
# from/to span requested). This is far denser than the daily-bar EURUSD
# project: a mean-reversion pairs strategy on 15-min bars needs enough
# distinct trades for statistical power, which a sparse daily signal
# can't provide -- but a multi-year 5-min pull is not feasible through
# this environment's data relay, so the window is bounded deliberately.
# Split roughly 60/40 for in-sample calibration / out-of-sample validation
# in v5.0 (see IN_SAMPLE_END_DATE).
IN_SAMPLE_END_DATE = "2026-06-16"

# -- PAIRS SPREAD --
HEDGE_RATIO_LOOKBACK_BARS = 2000  # ~21 days of 15-min bars for the rolling OLS beta (v4.0+); v1-v3 use one static beta fit once on in-sample data.
# A THIRD real v4.0 bug, found after fixing the jump-discontinuity one: the
# initial 480-bar (~5-day) lookback gave a genuinely unstable OLS estimate
# -- raw beta on rolling 480-bar windows ranged from 0.015 to 1.53 across
# this sample (stdev 0.31), because over only 5 days neither pair moves
# enough for the regression to pin down a reliable slope; noise dominates.
# Measured stdev drops to 0.12 at a 3000-bar (~31-day) lookback. 2000 bars
# (~21 days) is the compromise used here: meaningfully more stable (stdev
# 0.20) while not consuming so much of this 89-day dataset in warmup that
# there's nothing left to backtest.
HEDGE_RATIO_UPDATE_EVERY_BARS = 96  # only used if HEDGE_RATIO_EWMA_ALPHA is None -- see pairs.rolling_hedge_ratios docstring for why a hard step-update was ALSO a real v4.0 bug (300x spread jump at each update boundary)
HEDGE_RATIO_EWMA_ALPHA = 0.03      # the actual fix: EWMA-smoothed beta, responsive without noise spikes or discrete jumps
ZSCORE_LOOKBACK_BARS = 96         # ~1 trading day of 15-min bars for the rolling mean/std of the spread
ENTRY_ZSCORE = 2.0                # enter when |z| crosses above this
EXIT_ZSCORE = 0.25                # exit (take profit via reversion) when |z| crosses back below this -- NOT a fixed price target, a statistical one
MAX_HOLD_BARS = 192               # ~2 trading days of 15-min bars; safety cap if reversion never happens

# -- STOP LOSS --
# No hard take-profit (per the user's explicit instruction) -- the exit is
# the spread reverting to near zero. But a stop is mandatory: the single
# biggest real risk in pairs trading is the relationship breaking down
# (e.g. one central bank surprises, one economy decouples) and the spread
# never reverting, or blowing further out. The stop is expressed in
# z-score space (how far the spread has diverged, not a fixed % on either
# leg) since that is what actually threatens a stat-arb trade.
STOP_ZSCORE = 3.5

# -- REGIME FILTER (v2.0+) --
# A variance-ratio test: for a true mean-reverting series, the variance of
# k-bar returns should grow slower than linearly in k (sub-diffusive). For
# a trending/random-walk series it grows linearly or faster. VR < 1 (below
# the threshold) indicates mean-reverting behavior; only trade when the
# recent spread passes this test. This is the "quantify it, don't eyeball
# it" version of a regime filter -- not RSI/ADX dressed up.
REGIME_LOOKBACK_BARS = 480
REGIME_VR_K = 8                   # bars ahead for the variance-ratio test
REGIME_VR_THRESHOLD = 0.85        # require VR(k) < this to trade

# -- EVENT FILTER (v3.0+) --
# High-impact scheduled releases for the three currencies in play, pulled
# from FMP's economic calendar (129 events over the backtest window).
# Correlation-breakdown risk is highest right around these -- e.g. a US
# CPI surprise moves EURUSD and GBPUSD by different amounts because their
# non-USD legs don't share the same shock, which is exactly the "spread
# stops behaving like a stable relationship" risk this filter targets.
EVENTS_FILE = "fx_statarb_strategy/data/high_impact_events.json"
EVENT_CURRENCIES = ("USD", "EUR", "GBP")
EVENT_BLACKOUT_MINUTES_BEFORE = 30
EVENT_BLACKOUT_MINUTES_AFTER = 60

# -- SIZING (v4.0+) --
VOL_TARGET_DAILY = 0.01          # target 1% daily portfolio vol per open trade
INITIAL_CAPITAL = 10_000.0

REPORTS_DIR = "fx_statarb_strategy/reports"
