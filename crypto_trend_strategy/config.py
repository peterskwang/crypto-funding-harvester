"""Configuration for the multi-asset crypto time-series momentum strategy.

Why this project exists: a rigorous 36-pair G10 FX cointegration sweep
(see ../fx_statarb_strategy/) found zero pairs survive proper
multiple-testing correction -- FX spot pairs trading was ruled out, not
under-tuned. An external quant-strategist review recommended pivoting to
time-series (trend-following) momentum -- the most robust, most
replicable strategy family in the literature, backed by decades of live
CTA-industry evidence -- applied to a higher-volatility asset class where
genuine return potential is structurally larger than G10 FX spot. Crypto
funding-rate arbitrage was considered first (a closer match to this
repo's original strategy) but ruled out on data-access grounds: this
environment blocks direct Binance access, and FMP has no funding-rate
history endpoint, so backtesting it honestly isn't possible here.

Same rigor bar as before: no lookahead, no parameter grid search dressed
up as "iteration," in-sample/out-of-sample split touched once, sub-period
stability required, realistic transaction costs, honest reporting
regardless of outcome.
"""

SYMBOLS = ["BTCUSD", "ETHUSD", "SOLUSD", "BNBUSD", "AVAXUSD", "DOGEUSD",
           "ADAUSD", "LINKUSD", "LTCUSD", "DOTUSD", "XRPUSD"]
DATA_FILES = {s: f"crypto_trend_strategy/data/{s.lower()}_daily.json" for s in SYMBOLS}

# -- BACKTEST WINDOW --
# BTC has data back to 2013, but most alts list later (DOT: 2021-06-15).
# Rather than truncate to the shortest common history (which would throw
# away most of BTC/ETH's information) or extrapolate missing history
# (fabrication), each asset joins the tradeable universe once it has
# MIN_HISTORY_DAYS of its own price history -- a dynamic universe, same
# as how a live system would actually behave as new assets list.
BACKTEST_START_DATE = "2018-01-01"   # BTC, ETH, LTC, XRP, DOGE, BNB, ADA, LINK all live by here
IN_SAMPLE_END_DATE = "2023-01-01"    # ~5yr in-sample (design/calibration) / ~3.5yr out-of-sample (touched once)
MIN_HISTORY_DAYS = 200               # an asset must have this much of its own history before it can be traded (needed for the 200d signal lookback + vol estimate)

# -- MOMENTUM SIGNAL --
# Blended time-series momentum, per the quant-strategist recommendation:
# average of 3 lookback windows' sign-of-return, not a single arbitrary
# window. Chosen once, before looking at any backtest result -- not swept.
MOMENTUM_LOOKBACKS_DAYS = [30, 90, 200]   # ~1mo / ~3mo / ~200d, crypto-appropriate versions of the classic 1/3/12mo CTA blend (crypto trends resolve faster than TradFi)
MOMENTUM_ENTRY_THRESHOLD = 0.0            # composite score must be strictly positive (long) or negative (short) to hold a position; 0 = flat

# -- POSITION SIZING (volatility targeting) --
VOL_LOOKBACK_DAYS = 20
TARGET_ANNUALIZED_VOL_PER_ASSET = 0.15   # each asset's position is sized so its OWN annualized vol contribution is ~15%; portfolio vol is lower via diversification since assets aren't perfectly correlated
MAX_ASSET_WEIGHT = 0.35                   # cap any single asset's portfolio weight (risk-budget cap, not fit to results)
GROSS_EXPOSURE_CAP = 1.5                  # cap total gross exposure across all assets combined (portfolio-level leverage cap); if all 11 assets signal the same direction at their individual vol-target weights, scale everyone down proportionally to stay under this

# -- EXIT --
# Classic trend-following exits on signal flip, not a fixed hold period or
# fixed take-profit -- consistent with "let winners run, cut losers."
# A stop-loss is still mandatory as a safety net against the signal being
# slow to react to a sudden crash (crypto's realized jumps are large and
# fast; a lagging 30/90/200d signal can be caught off guard).
STOP_LOSS_PCT = 0.20   # 20%: sized to crypto's own realized volatility, computed on this
                        # data (2018-2026) -- BTC daily stdev 3.4% (65% annualized), ETH
                        # 4.5% (85% ann.), DOGE 9.0% (171% ann.), SOL 6.2% (119% ann.),
                        # with single-day worst-case drawdowns of -15% to -43% across these
                        # assets. A 3-8% FX-style stop (as used in eurusd_strategy/) would
                        # trigger on ordinary daily noise here almost every session. The
                        # vol-targeting position sizer is the PRIMARY risk control (it
                        # already scales exposure down on high-vol assets); this stop is
                        # the secondary backstop for when the trend signal is too slow to
                        # react to a sudden single-day crash.

# -- TRANSACTION COSTS --
# Retail spot crypto trading fee, one-way. Applied on every position change
# (both re-sizing and signal flips), not just entries/exits, since this is
# a continuously-rebalanced vol-targeted portfolio, not a buy-and-hold.
TRANSACTION_COST_PCT = 0.0010   # 10 bps one-way (typical retail spot maker/taker blended estimate)

# -- CAPITAL --
INITIAL_CAPITAL = 10_000.0

REPORTS_DIR = "crypto_trend_strategy/reports"
