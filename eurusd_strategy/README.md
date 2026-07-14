# EURUSD Velocity/Acceleration Strategy

A rules-based EURUSD swing strategy built from a user-provided Pine Script
indicator ("Flagship: Velocity and Acceleration Signals"), combined with an
EMA100 trend filter and an OHLC-derived volume-delta proxy.

> **Not investment advice.** Backtest only, on real historical daily bars
> (2013-2026), with a proper in-sample/out-of-sample split so a parameter
> search can't just report the best-looking overfit number. See `reports/`
> for the full writeup — the honest verdict there is that none of the
> configs tested show a solid, generalizable edge out-of-sample.

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
   simulation. Two exit modes: the original trailing stop (2%, sized off
   this instrument's own average daily range, capped at 20 trading days),
   and a fixed take-profit/stop-loss bracket exit (checked against intrabar
   high/low). Entries execute at the next bar's open after the signal bar
   closes — no lookahead.
6. **TP/SL search + validation** (`search_tp_sl.py`, `validate_oos.py`) —
   the data is split chronologically: 2013-2021 in-sample, 2022-2026
   out-of-sample. A 420-combo grid search over TP/SL/hold-period/filter
   combinations runs only on the in-sample window; the top candidates are
   then re-run **unmodified** on the untouched out-of-sample window. This
   is the actual defense against reporting an overfit "best" number as if
   it were a real edge.
7. **Report** (`strategy/report.py`, `run_backtest.py`) — renders the
   original trailing-stop result and its robustness sweep, the in-sample
   TP/SL search (top and bottom configs, not just the winner), and the
   out-of-sample validation with an explicit honest verdict.

## Data
`data/eurusd_daily.json` — 3579 real EURUSD daily bars (2013-01-02 to
2026-07-14) fetched from FMP. Daily bars were chosen deliberately over
intraday: fetching multiple years of 1H/4H forex bars through this
environment's data relay risks the same context-budget problem that hit the
pre-IPO project's multi-ticker fetch; a single instrument's daily history
(even 13 years of it) stayed within safe bounds because large tool results
auto-save to disk instead of flooding context.

## Usage
```
python -m eurusd_strategy.calibrate      # re-derive thresholds if data window changes
python -m eurusd_strategy.search_tp_sl   # in-sample TP/SL grid search
python -m eurusd_strategy.validate_oos   # out-of-sample validation of selected configs
python -m eurusd_strategy.run_backtest   # run everything, save the combined report
pytest tests/test_eurusd_indicators.py tests/test_eurusd_backtest.py
```

## Known limitations (see the backtest report for the full list)
- **The honest headline finding: no config tested shows a solid,
  generalizable out-of-sample edge.** The best in-sample total return
  (+11.5%) degraded to +0.50% out-of-sample; the best in-sample win rate
  (80.7%) held up better in relative terms (72.7% OOS) but only produced
  +0.61% OOS total return over 4.5 years — both below simple buy-and-hold.
- Volume delta is a proxy, not real order flow.
- No transaction costs modeled (spread/swap/slippage) — would likely erode
  what little edge these numbers show.
- Single instrument, single indicator family.
- Daily-bar swing read on an indicator that's timeframe-agnostic and often
  run intraday.
