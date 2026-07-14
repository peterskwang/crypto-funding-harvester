# EURUSD Velocity/Acceleration Strategy

A rules-based EURUSD swing strategy built from a user-provided Pine Script
indicator ("Flagship: Velocity and Acceleration Signals"), combined with an
EMA100 trend filter and an OHLC-derived volume-delta proxy.

> **Not investment advice.** Backtest only, on real historical daily bars,
> with full methodology and limitations disclosed in the report. Sample
> size is small (8-10 trades over 2 years) -- treat results as directional,
> not as a proven edge. See `reports/` for the full writeup.

This currently lives inside `crypto-funding-harvester` alongside the
unrelated `pre_ipo_screener/` project, for the same reason: no permission
yet to create a separate repo. Self-contained under `eurusd_strategy/` so it
can be lifted out later.

## How it works
1. **Signal** (`strategy/indicators.py`) — a 1:1 Python translation of the
   provided Pine Script: `velocity` = mean of `(close-close[i])/i` over a
   14-bar lookback, smoothed with a 20-period EMA; `acceleration` = the same
   recurrence applied to `velocity` itself. `strong_up`/`strong_down` fire on
   a threshold crossover of smoothed velocity confirmed by acceleration sign
   agreement — exactly the Pine Script's `strongUp`/`strongDown` logic.
2. **Threshold calibration** (`calibrate.py`) — Pine's default thresholds
   (±0.01) are sized for stock prices in the tens/hundreds of dollars.
   EURUSD's price scale is ~100x smaller, so the thresholds are re-derived
   as ~1 standard deviation of this instrument's own smoothedVelocity
   series — a one-time unit conversion, not a backtest-fit parameter.
3. **Trend filter** — EMA100: longs only taken above it, shorts only below.
4. **Volume delta proxy** — forex spot has no consolidated tape or real
   order-flow data. This approximates a buy/sell split from each bar's OHLC
   (Chaikin-style close-location split of the feed's tick-count volume) and
   requires it to agree with the signal direction. Disclosed as an
   approximation everywhere it's used.
5. **Backtest** (`strategy/backtest.py`) — single-position-at-a-time
   simulation with a trailing-stop exit (2%, sized off this instrument's own
   average daily range) capped at a 20-day max hold. Entries execute at the
   next bar's open after the signal bar closes — no lookahead.
6. **Report** (`strategy/report.py`, `run_backtest.py`) — renders the
   primary result plus a full parameter robustness sweep (not just the
   best-looking configuration), a buy-and-hold benchmark, and explicit
   limitations.

## Data
`data/eurusd_daily.json` — 586 real EURUSD daily bars (2024-07-15 to
2026-07-14) fetched from FMP. Daily bars were chosen deliberately over
intraday: fetching a year+ of 1H/4H forex bars through this environment's
data relay risks the same context-budget problem that hit the pre-IPO
project's multi-ticker fetch; a single instrument's daily history is well
within the range already proven safe there.

## Usage
```
python -m eurusd_strategy.calibrate      # re-derive thresholds if data window changes
python -m eurusd_strategy.run_backtest   # run backtest + robustness sweep, save report
pytest tests/test_eurusd_indicators.py tests/test_eurusd_backtest.py
```

## Known limitations (see the backtest report for the full list)
- Small sample size (8-10 trades) — not statistically significant.
- Volume delta is a proxy, not real order flow.
- No transaction costs modeled (spread/swap/slippage).
- Single instrument, single 2-year window.
- Daily-bar swing read on an indicator that's timeframe-agnostic and often
  run intraday.
