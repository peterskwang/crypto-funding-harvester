"""Configuration for the pre-IPO screener."""

# -- UNIVERSE WINDOWS --
LOOKAHEAD_DAYS = 45   # how far out to scan for upcoming IPOs
LOOKBACK_DAYS = 120   # how far back to pull the historical reference pool

# -- NOISE FILTER --
# The IPO calendar feed is dominated by ETFs, SPAC shells (units/warrants/rights),
# trusts, and bond/leveraged funds. Drop anything whose name/security type matches these.
EXCLUDE_NAME_KEYWORDS = [
    "ETF", "ETN", "TRUST", "ACQUISITION CORP", "ACQUISITION CORPORATION",
    "ACQUISITION COMPANY", "UNITS", "WARRANT", "RIGHTS", " FUND",
    "BOND", "DEPOSITARY SHARES", "WHEN ISSUED", "SPAC", "BLANK CHECK",
    "LIQUIDITY OPPORTUNITY VEHICLE",
]
EXCLUDE_TICKER_SUFFIXES = ["U", "W", "R", "WS", "RT"]  # common SPAC unit/warrant/rights suffixes

# Serial SPAC sponsors number their shells ("Acquisition I Corp", "Mountain Crest
# Acquisition 6 Corp", "Legato Merger Corp. IV", "GigCapital9 Corp.", "Cantor
# Equity Partners VII") — a numbered/roman-numeraled Acquisition/Capital/
# Investment/Merger/Partners entity is almost always a blank-check company, not
# an operating business. Matched against the uppercased name. Known tradeoff:
# this can also catch a handful of legitimate, long-established closed-end
# funds/BDCs that happen to use "Capital Corp" naming (e.g. Oxford Lane Capital
# Corp) — acceptable here since those aren't the kind of momentum IPO candidate
# this tool is built to surface anyway.
_ROMAN_OR_DIGIT = r"(?:I|II|III|IV|V|VI|VII|VIII|IX|X|\d{1,2})"
EXCLUDE_NAME_REGEXES = [
    r"ACQUISITIONS?\b.{0,25}\b(?:CORP|CO|COMPANY|INC|LTD|LIMITED)\b",
    rf"\b(?:CORP|CORPORATION|PARTNERS|HOLDINGS)\s+{_ROMAN_OR_DIGIT}\b",
    rf"(?:CAPITAL|INVESTMENT|MERGER)\s*{_ROMAN_OR_DIGIT}\b",
    r"\b(?:CAPITAL|INVESTMENT|MERGER)\s+CORP\b",
]

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
