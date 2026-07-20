"""Configuration for the ML entry-probability strategy.

The idea (third strategy angle this session, after FX pairs cointegration
-- ruled out -- and crypto trend-following -- underperforms buy-and-hold
out-of-sample): instead of a hand-designed rule ("enter when X crosses Y"),
objectively label every historical bar as a good/bad entry using a
triple-barrier method, engineer a set of backward-looking market-state
features (volume, volume delta, ATR, price acceleration, volume profile),
and train a calibrated probability model. The deliverable isn't "a
strategy that returns N%" so much as "does this model's stated probability
actually mean what it says" -- validated by checking real out-of-sample
hit rates per predicted-probability bucket, not asserted.

Labels are built by looking FORWARD from each candidate bar (did price
hit the profit target before the stop before time ran out) -- this is
standard supervised-learning label construction, not lookahead bias.
Lookahead bias would be computing FEATURES using future data; every
feature here is computed strictly from bars up to and including the
candidate bar, never after.
"""

SYMBOL = "BTCUSD"
DATA_FILE = "ml_entry_strategy/data/btcusd_5m.json"

# -- TIMEFRAME --
BASE_TIMEFRAME_MINUTES = 5
SIGNAL_TIMEFRAME_MINUTES = 15

# -- DATA WINDOW / SPLIT --
# ~89 days of 5-min bars (2026-04-21 to 2026-07-18), aggregated to 15-min
# (~8,540 bars). Split roughly 65/35 in-sample (train the model) /
# out-of-sample (validate calibration, touched once).
IN_SAMPLE_END_DATE = "2026-06-20"

# -- TRIPLE-BARRIER LABELING --
ATR_LOOKBACK = 14
PROFIT_TARGET_ATR_MULT = 1.5   # profit barrier = entry +/- 1.5x ATR
STOP_LOSS_ATR_MULT = 1.0       # stop barrier = entry -/+ 1.0x ATR (tighter than target -- asymmetric R:R, standard practice)
MAX_HOLD_BARS = 16             # ~4 hours at 15-min bars -- consistent with "frequent" entry/exit, not a multi-day hold

# -- FEATURES (all strictly backward-looking) --
VOLUME_ZSCORE_LOOKBACK = 40     # ~10 hours of 15-min bars for the rolling volume mean/std
PRICE_ACCEL_LOOKBACK = 4        # bars for the short-window acceleration (2nd derivative) calc
SURGE_LOOKBACK = 20             # bars for the "is this bar's range unusual" comparison
VOLUME_PROFILE_LOOKBACK = 96    # ~1 day of 15-min bars for the rolling volume-profile histogram
VOLUME_PROFILE_BINS = 24        # price bins for the volume profile histogram

# -- MODEL --
# Deliberately a simple, interpretable logistic regression, not a complex
# ML model -- with a few thousand labeled examples and several features,
# anything fancier (gradient boosting, neural nets) would be far more
# prone to overfitting the noise in a single 89-day window, exactly the
# trap this whole session has been about avoiding.
FEATURE_NAMES = [
    "volume_zscore", "volume_delta_norm", "atr_pct", "price_accel",
    "surge_ratio", "dist_from_poc_pct",
]
LOGISTIC_LR = 0.1
LOGISTIC_EPOCHS = 2000
LOGISTIC_L2 = 0.01   # small L2 penalty, chosen once (not swept) as a standard regularization default

# -- CALIBRATION VALIDATION --
CALIBRATION_BUCKET_EDGES = [0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]

REPORTS_DIR = "ml_entry_strategy/reports"
