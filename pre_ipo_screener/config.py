"""Configuration for the pre-IPO screener."""

# -- UNIVERSE WINDOWS --
LOOKAHEAD_DAYS = 45   # how far out to scan for upcoming IPOs
LOOKBACK_DAYS = 120   # how far back to pull the historical reference pool

# -- NOISE FILTER --
# Polygon's IPO feed is dominated by ETFs, SPAC shells (units/warrants/rights),
# trusts, and bond funds. Drop anything whose name/security type matches these.
EXCLUDE_NAME_KEYWORDS = [
    "ETF", "TRUST", "ACQUISITION CORP", "ACQUISITION CORPORATION",
    "ACQUISITION COMPANY", "UNITS", "WARRANT", "RIGHTS", " FUND",
    "BOND", "DEPOSITARY SHARES", "WHEN ISSUED",
]
EXCLUDE_TICKER_SUFFIXES = ["U", "W", "R", "WS", "RT"]  # common SPAC unit/warrant/rights suffixes

# -- DEAL SIZE TIERS (total offer size in USD) --
DEAL_SIZE_TIERS = {
    "micro": (0, 75_000_000),
    "small": (75_000_000, 300_000_000),
    "mid": (300_000_000, 1_000_000_000),
    "large": (1_000_000_000, float("inf")),
}

# -- PERFORMANCE WINDOWS (trading days since listing) --
DAY1_WINDOW = 1
WEEK1_WINDOW = 5
MONTH1_WINDOW = 21

# -- SCORING WEIGHTS (upcoming/long candidates) --
SCORE_WEIGHT_ANALOG_RETURN = 0.5
SCORE_WEIGHT_DEAL_SIZE = 0.25
SCORE_WEIGHT_PROXIMITY = 0.25
LONG_SCORE_WATCH_THRESHOLD = 55  # below this, candidate is WATCH not LONG

# -- FADE / SHORT DETECTION --
FADE_DAY1_POP_THRESHOLD = 0.15      # >=15% day-1 pop considered a "hot" open
FADE_DECAY_THRESHOLD = -0.08        # subsequent -8% off highs flags a fade
LOCKUP_WINDOW_DAYS = (90, 180)      # typical lockup-expiry short watch window

# -- SUGGESTED STYLE VOLATILITY CUTOFFS (realized daily stdev) --
HIGH_VOLATILITY_CUTOFF = 0.06
MODERATE_VOLATILITY_CUTOFF = 0.03

# -- OUTPUT --
TOP_N_PER_BUCKET = 5
REPORTS_DIR = "pre_ipo_screener/reports"
STATE_FILE_PATH = "pre_ipo_screener/state/screener_state.json"
