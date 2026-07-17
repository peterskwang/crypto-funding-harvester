# EURUSD/GBPUSD Statistical-Arbitrage Pairs Strategy

A Jim Simons-style strategy: not a technical indicator on either pair
individually, but a trade on the statistical relationship BETWEEN them.
EURUSD and GBPUSD are structurally correlated (0.83 measured return
correlation on this data, both USD-legs with overlapping European
economics). This trades the spread (log EURUSD - beta * log GBPUSD),
betting on reversion when it diverges and standing aside when the
relationship itself looks statistically unstable.

> **Not investment advice.** Backtest on ~89 days of real 15-min bars
> (5-min data aggregated, since FMP has no native 15-min forex endpoint),
> with genuine walk-forward validation. Honest headline: v5.0's
> out-of-sample result is real (didn't collapse relative to in-sample) but
> small -- **+0.16%/month equivalent**, nowhere near the 5%/month target
> stated at the outset. See `reports/` for the full writeup.

Lives inside `crypto-funding-harvester` alongside the other unrelated
strategy projects here, for the same reason as the others (no permission
yet to create a separate repo).

## How it works
1. **Data** (`strategy/bars.py`) — 5-min EURUSD/GBPUSD bars aggregated to
   15-min, inner-joined on timestamp so both legs of every bar are real.
2. **Spread** (`strategy/pairs.py`) — hedge ratio (beta) via OLS on log
   prices, spread = log(EURUSD) - beta*log(GBPUSD), rolling z-score of the
   spread, and a Lo-MacKinlay variance-ratio test for regime detection
   (quantified mean-reversion check, not RSI/ADX dressed up).
3. **Events** (`strategy/events.py`) — mechanical blackout window around
   129 real high-impact USD/EUR/GBP releases (FMP economic calendar).
4. **Backtest** (`strategy/backtest.py`) — one pairs-position at a time,
   entries on z-score threshold crossings, **no fixed take-profit** (exit
   is the spread statistically reverting, i.e. z-score returning near
   zero), a z-score-based **stop-loss** for when the relationship simply
   doesn't revert.
5. **Versions v1.0 -> v5.0** — each fixes one concrete, measured flaw in
   the previous one, including three real bugs found and documented while
   building v4.0 (every-bar re-estimation noise, discrete beta-update
   jump artifacts, and phantom P&L from a time-varying spread series —
   see the report for the full postmortem on each). v5.0 is evaluated
   with a genuine in-sample/out-of-sample split, not re-tuned to make the
   final number look good.

## Data
`data/eurusd_5m.json`, `data/gbpusd_5m.json` — ~18.5k real 5-min bars each
(2026-04-19 to 2026-07-16), fetched from FMP in 10-day chunks (the API
caps each call at roughly that range). `data/high_impact_events.json` —
129 real high-impact USD/EUR/GBP macro releases over the same window.

## Usage
```
python -m fx_statarb_strategy.run_backtest   # run v1.0-v5.0 + walk-forward validation, save report
pytest tests/test_fx_statarb_pairs.py tests/test_fx_statarb_backtest.py tests/test_fx_statarb_bars.py
```

## Known limitations (see the report for the full list)
- Small sample: 89 days total, ~31 days out-of-sample.
- No transaction costs modeled — likely material at these return magnitudes.
- 15-min execution, not a full 1-min backtest (data volume infeasible) —
  but a real 1-min slippage sample was measured and is comparable in size
  to the strategy's average per-trade edge, which is itself worth knowing.
- The regime filter and the rolling/EWMA beta don't compose cleanly (see
  report); v5.0 uses an in-sample-fit static beta instead.
