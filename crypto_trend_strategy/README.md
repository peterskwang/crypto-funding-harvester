# Crypto Multi-Asset Trend-Following Strategy

A vol-targeted, multi-asset time-series momentum strategy across 11 liquid
cryptocurrencies. Built as the second legitimate strategy angle tested in
this repo, after a rigorous 36-pair G10 FX cointegration sweep
(`fx_statarb_strategy/`) found zero pairs survive proper statistical
correction. An external quant-strategist review recommended time-series
trend-following as the most robust, replicable strategy family available,
applied here to crypto for its structurally higher volatility (and
therefore higher return *potential* -- not a guarantee).

> **Not investment advice.** Honest headline: in-sample (2018-2023) looks
> spectacular (+91.7% CAGR), but that's driven almost entirely by 2021's
> historic bull run (+1340% that year alone). Out-of-sample (2023-2026,
> touched once, not re-tuned) the strategy **lost money** (-6.4% CAGR)
> and badly underperformed simply buying and holding BTC (+290.1% over
> the same window). See `reports/` for the full writeup.

## How it works
1. **Data** (`strategy/data.py`) — daily bars for BTC, ETH, SOL, BNB,
   AVAX, DOGE, ADA, LINK, LTC, DOT, XRP (2013/listing-date to 2026-07-18),
   dynamic universe (each asset joins once it has its own history).
2. **Signal** (`strategy/signals.py`) — blended time-series momentum
   across 30/90/200-day lookbacks, each risk-adjusted by trailing
   realized vol before averaging.
3. **Sizing** — volatility-targeted per asset (constant risk contribution,
   not equal-dollar), capped per-asset and at the portfolio gross-exposure
   level.
4. **Backtest** (`strategy/backtest.py`) — daily-rebalanced, stateful
   (tracks entry price per asset for the stop-loss, cooldown after a stop
   until the signal genuinely changes), turnover-based transaction costs.
   Signal-flip exit (classic trend-following, no fixed take-profit); a
   20% stop-loss sized to crypto's own realized volatility as a backstop.

## Why crypto funding-rate arbitrage wasn't attempted instead
This repo's original strategy is funding-rate harvesting on Binance
perpetuals. That would have been the most direct "different angle," but
this environment blocks direct network access to Binance, and FMP (the
data source available via MCP relay all session) has no funding-rate
history endpoint. Rather than fabricate funding-rate data, this project
uses real, verifiable spot price data instead and tests trend-following,
which needed only price history.

## Data
`data/*_daily.json` — real daily OHLC bars per coin, fetched from FMP.
BTC has the longest history (2013-01-01); other coins start at their
actual listing dates (e.g., DOT: 2021-06-15).

## Usage
```
python -m crypto_trend_strategy.run_backtest   # run full backtest + IS/OOS split, save report
pytest tests/test_crypto_trend_signals.py tests/test_crypto_trend_backtest.py
```

## Known limitations (see the report for the full list)
- Out-of-sample result is negative and underperforms buy-and-hold badly —
  the honest headline finding, not a footnote.
- One out-of-sample window, one historical path.
- No slippage modeling beyond a flat 10bps cost.
- Today's liquid-11 universe, not a point-in-time-correct historical universe.
- No short-side funding/borrow costs modeled.
