# EURUSD Velocity/Acceleration Strategy -- Backtest Report

**Not investment advice.** This is a rules-based backtest of a translated technical indicator against historical EURUSD daily bars. Forex spot has no consolidated tape or true order-flow data -- "volume" and "volume delta" here are a tick-count proxy, not executed size or real aggressor flow. No transaction costs (spread, swap, slippage) are modeled. Every number below, including the out-of-sample section, is a backtest artifact, not a live-trading track record -- treat it accordingly.

## Methodology
- **Instrument:** EURUSD
- **Data window:** 2013-01-02 to 2026-07-14 (3579 daily bars)
- **Signal:** 1:1 Python translation of the provided Pine Script "Flagship: Velocity and Acceleration Signals" indicator (lookback=14, velocity EMA=20, smoothAccel=False).
- **Thresholds:** up=0.00099, down=-0.00099 -- derived once as ~1 standard deviation of the IN-SAMPLE (2013-2021) smoothedVelocity series only, not tuned against backtest results and not leaking the out-of-sample window.
- **Trend filter:** EMA100; longs only above it, shorts only below it.
- **Volume delta:** OHLC close-location proxy (buy/sell split of tick-count volume), required to agree with signal direction when enabled. This is a well-known approximation, not real order-flow -- forex has no centralized tape.
- **Entry timing:** next bar's open after the signal bar closes -- no lookahead.
- **Position management:** one trade at a time; a signal firing mid-trade is ignored.

## Part 1: Original trailing-stop config (unchanged from the first report)
- **Trades:** 60 over 3579 bars
- **Win rate:** 41.7%
- **Avg return/trade:** -0.05%
- **Total return (sum of trade returns):** -2.99%
- **Max drawdown:** 12.48%
- **Buy-and-hold EURUSD over the same window:** -13.15%

### Trailing-stop parameter robustness (same signal engine, varying one thing at a time)
| Round | Trades | Win Rate | Avg Return | Total Return | Max DD |
|---|---|---|---|---|---|
| Raw signal (no EMA100, no delta) | 75 | 41.3% | -0.07% | -5.22% | 16.90% |
| + EMA100 trend filter only | 72 | 41.7% | -0.02% | -1.51% | 13.73% |
| + Volume delta filter only | 63 | 41.3% | -0.11% | -6.70% | 15.70% |
| Primary (EMA100 + delta) | 60 | 41.7% | -0.05% | -2.99% | 12.48% |
| Trail 1.0% | 64 | 42.2% | +0.12% | +7.80% | 8.07% |
| Trail 1.5% | 61 | 37.7% | +0.11% | +6.44% | 10.52% |
| Trail 3.0% | 59 | 47.5% | -0.03% | -1.52% | 10.37% |
| Trail 5.0% | 56 | 46.4% | -0.08% | -4.66% | 13.59% |
| Max hold 10d | 67 | 47.8% | -0.05% | -3.45% | 9.74% |
| Max hold 15d | 62 | 43.5% | -0.15% | -9.01% | 13.05% |
| Max hold 30d | 58 | 36.2% | -0.17% | -9.92% | 14.68% |
| Max hold 45d | 57 | 29.8% | -0.36% | -20.42% | 23.76% |

## Part 2: Fixed take-profit / stop-loss search (in-sample only, 2013-2021)
Requested follow-up: instead of only a trailing stop, this searches fixed TP/SL bracket exits (checked against intrabar high/low, same-bar TP+SL ties resolved conservatively to the stop-loss) combined with EMA100/volume-delta filter on-off and hold-period, 420 configurations total, requiring at least 15 trades per config to be considered. **This search only ever looked at bars before 2022-01-01** -- see Part 3 for what happens when the results are checked against data the search never saw.

**Top 10 by in-sample total return:**
| EMA100 | Delta | Hold | TP | SL | Trades | Win Rate | Avg Return | Total Return | Max DD |
|---|---|---|---|---|---|---|---|---|---|
| True | True | 20d | 5.0% | 1.5% | 41 | 43.9% | +0.28% | +11.50% | 9.27% |
| True | True | 30d | 4.0% | 1.5% | 39 | 41.0% | +0.23% | +9.03% | 8.92% |
| True | True | 20d | 4.0% | 1.5% | 41 | 43.9% | +0.22% | +8.97% | 9.13% |
| False | True | 20d | 5.0% | 1.5% | 44 | 40.9% | +0.16% | +7.00% | 13.12% |
| False | False | 20d | 0.5% | 1.5% | 57 | 80.7% | +0.11% | +6.50% | 4.50% |
| False | False | 30d | 0.5% | 1.5% | 57 | 80.7% | +0.11% | +6.50% | 4.50% |
| True | True | 30d | 5.0% | 1.5% | 39 | 41.0% | +0.16% | +6.40% | 12.24% |
| True | True | 30d | 4.0% | 0.5% | 45 | 20.0% | +0.14% | +6.25% | 4.41% |
| True | True | 20d | 5.0% | 0.5% | 46 | 19.6% | +0.13% | +5.86% | 5.16% |
| False | False | 30d | 0.5% | 3.0% | 55 | 87.3% | +0.11% | +5.86% | 6.89% |

**Bottom 5 (shown for contrast -- the search space is not uniformly profitable; a lot of TP/SL combinations lose money on the same signal, same data):**
| EMA100 | Delta | Hold | TP | SL | Trades | Win Rate | Avg Return | Total Return | Max DD |
|---|---|---|---|---|---|---|---|---|---|
| False | False | 20d | 2.0% | 3.0% | 49 | 44.9% | -0.44% | -21.42% | 24.82% |
| False | False | 20d | 5.0% | 3.0% | 49 | 38.8% | -0.45% | -21.97% | 25.92% |
| True | False | 20d | 3.0% | 3.0% | 46 | 41.3% | -0.50% | -23.13% | 25.72% |
| False | False | 20d | 3.0% | 3.0% | 49 | 40.8% | -0.47% | -23.26% | 25.87% |
| False | False | 20d | 4.0% | 3.0% | 49 | 38.8% | -0.48% | -23.50% | 26.84% |

## Part 3: Out-of-sample validation (the actual test)
In-sample: 2013-01-02 to 2021-12-31, buy-and-hold -13.66%. Out-of-sample: 2022-01-03 to 2026-07-14, buy-and-hold +1.39%. Each config below was picked from the Part 2 search using only in-sample numbers, then run **once, unmodified**, against the out-of-sample window.

| Config | Sample | Trades | Win Rate | Total Return | Max DD |
|---|---|---|---|---|---|
| Best in-sample total_return (EMA+delta, hold=20d, tp=5%, sl=1.5%) | in-sample | 41 | 43.9% | +11.50% | 9.27% |
| Best in-sample total_return (EMA+delta, hold=20d, tp=5%, sl=1.5%) | out-of-sample | 21 | 47.6% | +0.50% | 5.35% |
| Best in-sample win_rate (no filters, hold=20d, tp=0.5%, sl=1.5%) | in-sample | 57 | 80.7% | +6.50% | 4.50% |
| Best in-sample win_rate (no filters, hold=20d, tp=0.5%, sl=1.5%) | out-of-sample | 33 | 72.7% | +0.61% | 2.99% |
| Original trailing-stop config (from first report, unchanged) | in-sample | 39 | 38.5% | +1.19% | 12.48% |
| Original trailing-stop config (from first report, unchanged) | out-of-sample | 20 | 50.0% | -2.07% | 7.23% |

### Honest verdict
The config with the best in-sample total return (+11.5%, EMA100+delta filters, TP 5%/SL 1.5%) produced only +0.50% out-of-sample -- a large, classic degradation that indicates the in-sample number was substantially fit to that specific 9-year window rather than reflecting a durable edge. The config with the best in-sample win rate (80.7%, no filters, a tight TP 0.5%/SL 1.5%) held up better in relative terms (72.7% win rate out-of-sample) but its out-of-sample total return was still only +0.61% over 4.5 years -- both below the period's own buy-and-hold return. The original trailing-stop config went slightly negative out-of-sample (-2.07%). **None of the three configurations tested here show a solid, generalizable edge on this data.** A high win rate proved more robust than a high total return, which is a useful, real finding -- but it isn't the same as a strategy worth sizing up and trading.

## Appendix: Trade log (Part 1 primary config)
| Direction | Signal Date | Entry Date | Entry | Exit Date | Exit | Days | Return |
|---|---|---|---|---|---|---|---|
| LONG | 2013-01-25 | 2013-01-28 | 1.34569 | 2013-02-08 | 1.33629 | 9 | -0.70% |
| SHORT | 2013-02-22 | 2013-02-25 | 1.32161 | 2013-03-25 | 1.28524 | 20 | +2.75% |
| SHORT | 2013-05-22 | 2013-05-23 | 1.28580 | 2013-06-06 | 1.32454 | 10 | -3.01% |
| SHORT | 2013-07-04 | 2013-07-05 | 1.29135 | 2013-07-11 | 1.30959 | 4 | -1.41% |
| LONG | 2013-07-25 | 2013-07-26 | 1.32776 | 2013-08-23 | 1.33759 | 20 | +0.74% |
| LONG | 2013-10-22 | 2013-10-23 | 1.37813 | 2013-11-01 | 1.34902 | 7 | -2.11% |
| SHORT | 2013-11-08 | 2013-11-11 | 1.33570 | 2013-12-06 | 1.37023 | 19 | -2.59% |
| SHORT | 2014-05-28 | 2014-05-29 | 1.35906 | 2014-06-26 | 1.36101 | 20 | -0.14% |
| SHORT | 2014-08-25 | 2014-08-26 | 1.31919 | 2014-09-23 | 1.28464 | 20 | +2.62% |
| SHORT | 2014-12-05 | 2014-12-08 | 1.22878 | 2015-01-07 | 1.18394 | 20 | +3.65% |
| SHORT | 2015-02-27 | 2015-03-02 | 1.11819 | 2015-03-18 | 1.08604 | 12 | +2.88% |
| SHORT | 2015-04-10 | 2015-04-13 | 1.05846 | 2015-04-17 | 1.08000 | 4 | -2.04% |
| SHORT | 2015-06-01 | 2015-06-02 | 1.09245 | 2015-06-17 | 1.13354 | 11 | -3.76% |
| SHORT | 2015-07-15 | 2015-07-16 | 1.09413 | 2015-07-27 | 1.10847 | 7 | -1.31% |
| LONG | 2015-08-21 | 2015-08-24 | 1.13766 | 2015-08-26 | 1.13113 | 2 | -0.57% |
| SHORT | 2015-10-27 | 2015-10-28 | 1.10486 | 2015-11-25 | 1.06240 | 20 | +3.84% |
| LONG | 2016-02-04 | 2016-02-05 | 1.12059 | 2016-02-22 | 1.10271 | 11 | -1.60% |
| LONG | 2016-03-17 | 2016-03-18 | 1.13164 | 2016-04-15 | 1.12750 | 20 | -0.37% |
| SHORT | 2016-05-24 | 2016-05-25 | 1.11390 | 2016-06-03 | 1.13615 | 7 | -2.00% |
| LONG | 2016-08-18 | 2016-08-19 | 1.13522 | 2016-09-16 | 1.11499 | 20 | -1.78% |
| SHORT | 2016-10-14 | 2016-10-17 | 1.09685 | 2016-11-03 | 1.11039 | 13 | -1.23% |
| SHORT | 2016-11-15 | 2016-11-16 | 1.07187 | 2016-12-05 | 1.07632 | 13 | -0.42% |
| SHORT | 2016-12-15 | 2016-12-16 | 1.04123 | 2017-01-05 | 1.06049 | 12 | -1.85% |
| LONG | 2017-04-26 | 2017-04-27 | 1.09038 | 2017-05-25 | 1.12090 | 20 | +2.80% |
| LONG | 2017-06-29 | 2017-06-30 | 1.14386 | 2017-07-28 | 1.17491 | 20 | +2.71% |
| LONG | 2017-08-28 | 2017-08-29 | 1.19784 | 2017-09-26 | 1.17917 | 20 | -1.56% |
| LONG | 2018-01-02 | 2018-01-03 | 1.20581 | 2018-01-31 | 1.24132 | 20 | +2.94% |
| SHORT | 2018-04-30 | 2018-05-01 | 1.20775 | 2018-05-29 | 1.15393 | 20 | +4.46% |
| SHORT | 2018-10-29 | 2018-10-30 | 1.13726 | 2018-11-19 | 1.14522 | 14 | -0.70% |
| SHORT | 2020-02-13 | 2020-02-14 | 1.08390 | 2020-02-27 | 1.10000 | 9 | -1.49% |
| LONG | 2020-03-05 | 2020-03-06 | 1.12374 | 2020-03-12 | 1.11845 | 4 | -0.47% |
| SHORT | 2020-03-20 | 2020-03-23 | 1.07067 | 2020-03-26 | 1.10303 | 3 | -3.02% |
| LONG | 2020-07-20 | 2020-07-21 | 1.14472 | 2020-08-18 | 1.19313 | 20 | +4.23% |
| LONG | 2020-12-01 | 2020-12-02 | 1.20674 | 2020-12-31 | 1.22157 | 20 | +1.23% |
| LONG | 2021-01-05 | 2021-01-06 | 1.22925 | 2021-01-15 | 1.20747 | 7 | -1.77% |
| SHORT | 2021-03-08 | 2021-03-09 | 1.18461 | 2021-04-06 | 1.18739 | 20 | -0.23% |
| LONG | 2021-04-23 | 2021-04-26 | 1.20914 | 2021-05-24 | 1.22137 | 20 | +1.01% |
| SHORT | 2021-06-18 | 2021-06-21 | 1.18559 | 2021-07-19 | 1.17969 | 20 | +0.50% |
| SHORT | 2021-11-15 | 2021-11-16 | 1.13674 | 2021-12-14 | 1.12585 | 20 | +0.96% |
| SHORT | 2022-04-12 | 2022-04-13 | 1.08265 | 2022-05-11 | 1.05121 | 20 | +2.90% |
| SHORT | 2022-07-05 | 2022-07-06 | 1.02646 | 2022-07-19 | 1.02241 | 9 | +0.39% |
| SHORT | 2022-08-22 | 2022-08-23 | 0.99411 | 2022-09-12 | 1.01214 | 14 | -1.81% |
| SHORT | 2022-09-23 | 2022-09-26 | 0.96671 | 2022-09-29 | 0.98154 | 3 | -1.53% |
| LONG | 2022-11-10 | 2022-11-11 | 1.02072 | 2022-12-09 | 1.05329 | 20 | +3.19% |
| LONG | 2023-01-12 | 2023-01-13 | 1.08522 | 2023-02-06 | 1.07253 | 16 | -1.17% |
| SHORT | 2023-02-24 | 2023-02-27 | 1.05430 | 2023-03-21 | 1.07653 | 16 | -2.11% |
| LONG | 2023-03-30 | 2023-03-31 | 1.09046 | 2023-04-28 | 1.10166 | 20 | +1.03% |
| SHORT | 2023-05-24 | 2023-05-25 | 1.07494 | 2023-06-15 | 1.09447 | 15 | -1.82% |
| LONG | 2023-07-13 | 2023-07-14 | 1.12262 | 2023-07-27 | 1.09752 | 9 | -2.24% |
| SHORT | 2023-09-07 | 2023-09-08 | 1.06957 | 2023-10-06 | 1.05844 | 20 | +1.04% |
| LONG | 2023-12-26 | 2023-12-27 | 1.10419 | 2024-01-16 | 1.08751 | 14 | -1.51% |
| SHORT | 2024-04-16 | 2024-04-17 | 1.06186 | 2024-05-15 | 1.08841 | 20 | -2.50% |
| LONG | 2024-08-19 | 2024-08-20 | 1.10849 | 2024-09-17 | 1.11132 | 20 | +0.26% |
| SHORT | 2024-10-15 | 2024-10-16 | 1.08904 | 2024-11-13 | 1.05622 | 20 | +3.01% |
| SHORT | 2025-01-02 | 2025-01-03 | 1.02610 | 2025-01-24 | 1.04918 | 15 | -2.25% |
| LONG | 2025-03-05 | 2025-03-06 | 1.07874 | 2025-04-02 | 1.08489 | 20 | +0.57% |
| LONG | 2025-04-10 | 2025-04-11 | 1.11982 | 2025-05-06 | 1.13665 | 20 | +1.50% |
| LONG | 2025-06-12 | 2025-06-13 | 1.15804 | 2025-07-07 | 1.17080 | 20 | +1.10% |
| LONG | 2026-01-27 | 2026-01-28 | 1.20395 | 2026-02-20 | 1.17818 | 20 | -2.14% |
| LONG | 2026-04-14 | 2026-04-15 | 1.17966 | 2026-05-08 | 1.17852 | 20 | -0.10% |

## Limitations
- **This is a validated-but-still-small sample.** Even at 13 years of daily bars, a strategy that trades a few dozen times a year only accumulates tens to low hundreds of trades -- enough to catch gross overfitting (Part 3 did), not enough to certify a genuine edge with statistical confidence.
- **Volume delta is a proxy**, not real order flow -- forex spot trading is decentralized/OTC with no consolidated tape.
- **No transaction costs modeled** (spread, swap/rollover, slippage). At sub-1% average trade returns, a few pips of round-trip cost would materially erode or erase these numbers.
- **Single instrument, single indicator family.** Not tested across other pairs.
- **Daily bars only** -- the original Pine Script is timeframe-agnostic and is often run intraday; this is a swing-timeframe read on the same logic.
