# EURUSD Velocity/Acceleration Strategy -- Backtest Report

**Not investment advice.** This is a rules-based backtest of a translated technical indicator against historical EURUSD daily bars. Forex spot has no consolidated tape or true order-flow data -- "volume" and "volume delta" here are a tick-count proxy, not executed size or real aggressor flow. Past performance, especially on a sample this small (single digit to low double-digit trades), is not indicative of future results and should not be extrapolated into a return expectation.

## Methodology
- **Instrument:** EURUSD
- **Data window:** 2024-07-15 to 2026-07-14 (586 daily bars)
- **Signal:** 1:1 Python translation of the provided Pine Script "Flagship: Velocity and Acceleration Signals" indicator (lookback=14, velocity EMA=20, smoothAccel=False).
- **Thresholds:** up=0.00088, down=-0.00088 -- derived once as ~1 standard deviation of this instrument's own smoothedVelocity series (see calibrate.py), not tuned against backtest results.
- **Trend filter:** EMA100; longs only above it, shorts only below it.
- **Volume delta:** OHLC close-location proxy (buy/sell split of tick-count volume), required to agree with signal direction. This is a well-known approximation, not real order-flow -- forex has no centralized tape.
- **Exit:** trailing stop at 2.0% off the running peak/trough since entry, capped at 20 trading days.
- **Entry timing:** next bar's open after the signal bar closes -- no lookahead.
- **Position management:** one trade at a time; a signal firing mid-trade is ignored.

## Headline Result (primary config: EMA100 + delta filters on)
- **Trades:** 10 over 586 bars (~5/year)
- **Win rate:** 50.0%
- **Avg return/trade:** +0.03%
- **Total return (sum of trade returns, not compounded sizing):** +0.32%
- **Max drawdown (equity curve, 1x sizing per trade):** 4.55%
- **Buy-and-hold EURUSD over the same window:** +5.12%

### Honest read
The strategy fires rarely -- roughly 5 signals a year in each direction after the trend and delta filters -- because both the velocity threshold and the acceleration-agreement condition are fairly strict. Longs were the stronger side (66.7% win rate) and shorts the weaker side (25% win rate) over this window; combined P&L across configurations tested below ranges from modestly positive to modestly negative and is smaller in magnitude than simply buying and holding EURUSD over the same two years. **With 8-10 trades, none of these numbers are statistically significant** -- this is a directional read on the mechanism, not proof of an edge.

A secondary honest caveat: at the calibrated 2% trailing-stop width, the stop rarely binds before the 20-day hold cap (see the trade table below -- most trades run the full 20 days). In practice this configuration behaves closer to a fixed 20-day hold with a disaster-stop safety net than to a responsive trailing exit; the robustness table shows what happens at tighter widths.

### Trade log (primary config)
| Direction | Signal Date | Entry Date | Entry | Exit Date | Exit | Days | Return |
|---|---|---|---|---|---|---|---|
| LONG | 2024-08-19 | 2024-08-20 | 1.10849 | 2024-09-17 | 1.11132 | 20 | +0.26% |
| SHORT | 2024-11-11 | 2024-11-12 | 1.06490 | 2024-12-10 | 1.05268 | 20 | +1.15% |
| SHORT | 2024-12-19 | 2024-12-20 | 1.03580 | 2025-01-21 | 1.04242 | 20 | -0.64% |
| LONG | 2025-03-05 | 2025-03-06 | 1.07874 | 2025-04-02 | 1.08489 | 20 | +0.57% |
| LONG | 2025-04-03 | 2025-04-04 | 1.10513 | 2025-04-30 | 1.13276 | 20 | +2.50% |
| LONG | 2025-06-12 | 2025-06-13 | 1.15804 | 2025-07-07 | 1.17080 | 20 | +1.10% |
| SHORT | 2025-07-31 | 2025-08-01 | 1.14172 | 2025-08-25 | 1.16204 | 20 | -1.78% |
| LONG | 2026-01-27 | 2026-01-28 | 1.20395 | 2026-02-20 | 1.17818 | 20 | -2.14% |
| LONG | 2026-04-14 | 2026-04-15 | 1.17966 | 2026-05-08 | 1.17852 | 20 | -0.10% |
| SHORT | 2026-06-23 | 2026-06-24 | 1.13837 | 2026-07-14 | 1.14520 | 17 | -0.60% |

## Rounds of Iteration (all shown, not just the best-looking one)
Each row below is a real backtest run over the same data and signal engine, varying one parameter at a time, to check whether the headline result is robust or a fragile artifact of one specific configuration. None of these were used to retroactively pick the "final" config -- the primary config above was fixed by the calibration/design rationale before this sweep was run.

| Round | Trades | Win Rate | Avg Return | Total Return | Max DD |
|---|---|---|---|---|---|
| Raw signal (no EMA100, no delta) | 11 | 54.5% | +0.14% | +1.59% | 3.88% |
| + EMA100 trend filter only | 11 | 54.5% | +0.14% | +1.59% | 3.88% |
| + Volume delta filter only | 10 | 50.0% | +0.03% | +0.32% | 4.55% |
| Primary (EMA100 + delta) | 10 | 50.0% | +0.03% | +0.32% | 4.55% |
| Trail 1.0% | 10 | 40.0% | -0.19% | -1.89% | 5.60% |
| Trail 1.5% | 10 | 30.0% | -0.18% | -1.84% | 4.48% |
| Trail 3.0% | 10 | 50.0% | +0.03% | +0.32% | 4.55% |
| Trail 5.0% | 10 | 50.0% | +0.03% | +0.32% | 4.55% |
| Max hold 10d | 10 | 50.0% | +0.09% | +0.91% | 4.63% |
| Max hold 15d | 10 | 50.0% | +0.22% | +2.21% | 4.11% |
| Max hold 30d | 9 | 33.3% | -0.17% | -1.52% | 7.39% |
| Max hold 45d | 8 | 25.0% | -0.38% | -3.04% | 9.71% |

## Limitations
- **Sample size.** 8-10 trades over 2 years is not enough to statistically distinguish this from noise. Treat every metric above as directional, not a reliable expectancy.
- **Volume delta is a proxy**, not real order flow -- forex spot trading is decentralized/OTC with no consolidated tape.
- **No transaction costs modeled** (spread, swap/rollover, slippage). EURUSD spreads are typically tight, but at ~0.3% average trade return, even a few pips of round-trip cost is a meaningful fraction of the edge.
- **Single 2-year window, single instrument.** Not tested across other pairs or market regimes (this window included both trending and range-bound stretches).
- **Daily bars only** -- the original Pine Script is timeframe-agnostic and is often run intraday; this backtest is a swing-timeframe read on the same logic, not a test of its intraday behavior.
