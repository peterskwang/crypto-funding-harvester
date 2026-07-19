# Crypto Multi-Asset Trend-Following Strategy -- Backtest Report

**Not investment advice.** This is a rules-based, vol-targeted multi-asset trend-following backtest on real daily crypto price data (2018-2026). Every number below, including the out-of-sample section, is a backtest artifact, not a live track record.

## Why this project exists
A rigorous 36-pair G10 FX cointegration sweep (see `fx_statarb_strategy/`) found zero pairs survive proper multiple-testing correction -- FX spot pairs trading was ruled out on the evidence, not under-tuned. An external quant-strategist review recommended pivoting to time-series (trend-following) momentum -- the most robust, most replicable strategy family in the literature -- applied to a higher-volatility asset class where genuine return potential is structurally larger than G10 FX spot. Crypto perpetual funding-rate arbitrage (the closer match to this repo's original strategy) was considered first but ruled out on data-access grounds: this environment blocks direct Binance access and FMP has no funding-rate history endpoint, so it can't be backtested honestly here.

## Methodology
- **Universe:** BTCUSD, ETHUSD, SOLUSD, BNBUSD, AVAXUSD, DOGEUSD, ADAUSD, LINKUSD, LTCUSD, DOTUSD, XRPUSD (11 liquid coins, dynamic universe -- each joins once it has its own price history, same as a live system).
- **Signal:** blended time-series momentum across [30, 90, 200] day lookbacks, each risk-adjusted by trailing realized vol before averaging (so a 30-day and a 200-day window contribute on a comparable scale).
- **Sizing:** volatility-targeted per asset (15% annualized vol target each, capped at 35% portfolio weight), portfolio gross exposure capped at 1.5x.
- **Exit:** signal-flip (classic trend-following, no fixed take-profit) plus a 20% stop-loss backstop sized to crypto's own realized volatility (BTC ~65% annualized, alts up to 170%+) -- a backstop for when the trend signal is too slow to react to a sudden crash, not the primary risk control.
- **Costs:** 0.10% one-way on every position change (turnover-based).
- **Split:** in-sample 2018-01-01 to 2023-01-01 (design/calibration), out-of-sample 2023-01-01 onward (touched once, not re-tuned after seeing it). No parameter grid search was run -- lookbacks, vol target, and stop-loss were each chosen once from the data's own statistics, not swept.

## Results
| Period | CAGR | Sharpe | Max Drawdown | Total Return |
|---|---|---|---|---|
| In-sample | +91.7% | 1.18 | 65.7% | +2498.3% |
| Out-of-sample | -6.4% | 0.24 | 69.9% | -21.0% |
| Full 2018-2026 | +41.3% | 0.83 | 73.8% | +1816.8% |

### Honest verdict
In-sample looked spectacular: +91.7% CAGR, Sharpe 1.18. **Out-of-sample the strategy actually lost money**: -6.4% CAGR, Sharpe 0.24, total return -21.0% over the held-out period. This is exactly the failure mode walk-forward validation exists to catch, and it caught it.

**The year-by-year breakdown explains why**: 2021 alone returned +1340.0% -- one historic crypto bull-market year is doing nearly all the work in the in-sample number. Every other year is decidedly mixed:

| Year | Return |
|---|---|
| 2018 | +34.3% |
| 2019 | -3.0% |
| 2020 | +108.7% |
| 2021 | +1340.0% |
| 2022 | -33.2% |
| 2023 | -8.5% |
| 2024 | +13.0% |
| 2025 | -37.4% |
| 2026 | +13.4% |

2022, 2023, and 2025 were all significant losing years (-33%, -9%, -37%); only 2024 and 2026-YTD were modestly positive. This is not a repeatable monthly edge -- it's one extraordinary regime (2020-2021 mania) followed by years of whipsaw and mixed results, which is a well-documented characteristic of trend-following: it captures sustained directional moves and bleeds slowly (or gets stopped out) in choppy, range-bound, or sharply-reversing markets.

### The number that matters most: versus doing nothing
| Period | Strategy | BTC buy-and-hold | ETH buy-and-hold |
|---|---|---|---|
| Full 2018-2026 | +1816.8% | +380.7% | +145.3% |
| In-sample | +2498.3% | +23.2% | +58.1% |
| Out-of-sample | -21.0% | +290.1% | +55.1% |

**Over the out-of-sample window -- the only honest forward-looking test -- simply buying and holding BTC returned +290.1% while this strategy returned -21.0%.** The vol-targeted trend book did not just fail to hit an ambitious target -- it destroyed value relative to the simplest possible alternative, during a period that was actually a strong bull market. The strategy's apparent edge over buy-and-hold in the full-sample number is entirely a 2021 artifact.

## What this means for the original 5%/month goal
Two structurally different, legitimate strategy families have now been tested with real rigor on real data: FX pairs cointegration (ruled out -- no pair in the entire G10 set survives multiple-testing correction) and crypto trend-following (tested here -- real full-sample returns, but they evaporate out-of-sample and underperform simple buy-and-hold in the most recent, most relevant period). Neither supports a 5%/month, consistently-achievable claim. This matches the external quant-strategist review's assessment: realistic systematic strategies at reasonable risk deliver high-single to low-double-digit annual returns at Sharpe ~0.5-1.0, not 80%/year. The honest path forward, if this is worth continuing, is either (a) accept a realistic target and size positions/leverage accordingly, or (b) if crypto exposure is the goal, seriously compare this strategy against simple buy-and-hold before adding the complexity, cost, and whipsaw risk of active trend-following on top of it.

## Limitations
- **One out-of-sample period, one asset class.** 3.5 years is a real forward test but still a single historical path -- crypto has had few full market cycles.
- **No slippage/liquidity modeling** beyond a flat 10bps cost -- in a sharp crash, real fills on smaller-cap alts (DOGE, AVAX, DOT) would likely be worse.
- **Survivorship**: the 11-coin universe is today's liquid majors, not a point-in-time-correct universe of what was liquid/tradeable in 2018.
- **No borrow/funding costs modeled for short positions** -- shorting crypto in practice carries real, sometimes substantial, funding costs this backtest ignores.
