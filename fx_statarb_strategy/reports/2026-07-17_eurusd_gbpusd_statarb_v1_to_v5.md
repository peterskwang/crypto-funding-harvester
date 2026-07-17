# EURUSD/GBPUSD Statistical-Arbitrage Pairs Strategy -- v1.0 to v5.0

**Not investment advice.** This is a rules-based statistical-arbitrage backtest on ~89 days of real EURUSD/GBPUSD 15-min bars (aggregated from 5-min data; the FMP forex API has no native 15-min endpoint). Every number below, including the out-of-sample section, is a backtest artifact on a short sample, not a live track record.

## Concept
Not a technical-indicator strategy on either pair individually. EURUSD and GBPUSD are structurally correlated (measured 0.83 return correlation on this data, both USD-legs with overlapping European economics) -- this trades the SPREAD between them (log EURUSD - beta * log GBPUSD). When the spread statistically diverges from its normal relationship, bet on reversion (long the cheap side, short the rich side); when the relationship itself looks statistically unstable, stand aside. No hard take-profit (exit is the spread reverting to near zero, not a fixed price target); a z-score-based stop-loss caps the risk of the relationship simply not reverting.

## Version-by-version progression
Each version fixes one concrete, measured flaw found in the previous one -- including three real bugs surfaced while building v4.0, kept visible here rather than silently patched, because how they were found is as informative as the fix.

| Version | Trades | Win Rate | Total Return | Max DD | What changed |
|---|---|---|---|---|---|
| v1.0 (baseline) | 125 | 59.2% | +1.27% | 0.88% | Static full-sample beta, no filters |
| v2.0 (+ regime filter) | 82 | 59.8% | +1.23% | 0.68% | Added variance-ratio mean-reversion regime filter |
| v3.0 (+ event filter) | 80 | 60.0% | +0.99% | 0.68% | Added high-impact USD/EUR/GBP macro release blackout |
| v4.0 (rolling beta + vol sizing, isolated) | 30 | 53.3% | +0.19% | 0.49% | EWMA-smoothed rolling beta (fixes v1.0's lookahead) + volatility-targeted sizing |

### v1.0 (baseline)
Baseline pairs stat-arb: one beta fit once on the FULL backtest window (a real, deliberate lookahead flaw kept visible here -- a live system on day 1 cannot know a beta fit using three months of future data), z-score entries/exits, z-score-based stop-loss, no take-profit target.

### v2.0 (+ regime filter)
Adds a quantified regime filter (Lo-MacKinlay variance-ratio test) so entries only fire when the spread is statistically mean-reverting over the recent window, not trending. Improved trade quality (higher avg return/trade, lower drawdown) but NOT total return -- fewer trades approximately offset the per-trade improvement. A real, honest tradeoff, not an unambiguous win.

### v3.0 (+ event filter)
Adds a mechanical blackout window (-30min/+60min) around 129 scheduled high-impact USD/EUR/GBP releases pulled from FMP's economic calendar, on the theory that correlation-breakdown risk spikes around surprise macro data. Measured effect on this sample: roughly neutral to slightly negative (total return 0.99% vs v2.0's 1.23%, from blocking just 2 trades that happened to be net positive). Genuinely inconclusive on this sample size -- not every plausible-sounding filter improves a backtest, and that's a real finding too.

### v4.0 (rolling beta + vol sizing, isolated)
Replaces the static full-sample beta with a strictly backward-looking, EWMA-smoothed rolling beta (alpha=0.03, 2000-bar/~21-day lookback) -- the actual fix for v1.0's lookahead flaw -- plus inverse-volatility position sizing. Three real bugs were found and fixed getting here (every-bar re-fit noise, discrete jump artifacts, phantom P&L from a time-varying spread -- see the report's bug section). Evaluated in isolation (no regime/event filter, since those don't compose cleanly with a time-varying beta -- see Limitations): fewer trades, lower total return than v1.0. A more methodologically correct beta doesn't automatically mean a more profitable one on a 3-month sample.

## v5.0: walk-forward validation (the actual test)
In-sample: 2026-04-19 17:00:00 to 2026-06-16 00:00:00, used to fit the hedge ratio (beta = 0.9471) and diagnose in-sample performance. Out-of-sample: 2026-06-16 00:00:00 to 2026-07-16 23:45:00 -- entries were mechanically blocked before this point (min_entry_index), so this is a genuine forward test on data the beta fit never saw, not a re-run over the same window.

| Sample | Trades | Win Rate | Total Return | Max DD | Period | Monthly-equivalent |
|---|---|---|---|---|---|---|
| In-sample | 59 | 62.7% | +0.65% | 0.60% | 57d | +0.34% |
| Out-of-sample | 26 | 57.7% | +0.16% | 0.47% | 30d | +0.16% |

### Honest verdict
In-sample: +0.34%/month equivalent. Out-of-sample: +0.16%/month equivalent. Both are far below the 5%/month target stated at the start of this exercise -- roughly 31x short on the out-of-sample number. The encouraging part: out-of-sample did NOT collapse relative to in-sample (no big overfitting signature like the EMA strategy showed) -- win rate held up (57.7% OOS vs 62.7% IS) and drawdown stayed low (0.47% OOS). This is a real, quantifiable, market-neutral edge, it is just a small one on this sample: consistent with a genuine but modest statistical relationship, not a fitted curve, and nowhere near a 5%/month return target without materially more leverage than the risk controls here would responsibly allow, or a much longer track record to size up on.

## Real bugs found and fixed during v4.0 (kept visible, not smoothed over)
1. **Every-bar beta re-estimation injects noise.** Re-fitting the OLS hedge ratio fresh on every 15-min bar sounds most responsive but quadrupled the spread's bar-to-bar volatility versus a static beta -- pure regression noise, which fully defeated the regime filter (0 trades passed it).
2. **Discrete step-updates create jump artifacts.** The naive fix -- re-fit only every N bars, hold beta fixed between updates -- traded that noise for large discontinuities: the median spread jump exactly at an update boundary measured ~300x the median jump elsewhere (0.031 vs 0.0001). Every trade in that configuration (37/37) hit its stop-loss on the artifact, not a real reversion failure.
3. **Phantom P&L from a time-varying spread series.** The trade P&L calculation read `exit_spread` from the same globally time-varying spread series used for live signal generation -- so if beta drifted between entry and exit, the "return" partly reflected the hedge ratio changing, not the price relationship moving. Fixed by recomputing the exit spread with the beta FIXED at entry, matching what a real fixed-notional position actually earns.
4. **480-bar (~5-day) hedge-ratio lookback was statistically unstable**: raw OLS beta on rolling 5-day windows ranged from 0.015 to 1.53 (stdev 0.31) on this data. Widening to 2000 bars (~21 days) cut that to stdev ~0.20 -- still not fully stable, a real, disclosed constraint of only having ~89 days of data to work with.

## 1-minute entry timing: validated on a sample, not fully backtested
The full backtest above executes at the 15-min bar's close, ~15 minutes after signal confirmation. A full 1-minute-granularity backtest across 89 days x 2 pairs was not feasible to fetch through this environment's data relay (1-min bars run ~1,440/day/pair vs ~69 15-min bars/day/pair). Instead, real 1-min data was pulled for a 6-trade sample from the out-of-sample period to measure what waiting the full 15 minutes actually costs: the mean absolute difference between the spread at the first available 1-min close (fast execution) versus the 15-min bar's close (what the backtest assumes) was **0.000108** in spread units -- comparable in magnitude to v1.0's average return PER TRADE (0.000102). In other words, execution speed here isn't a minor implementation detail: on this instrument and signal, how fast you can act on a confirmed signal is roughly as consequential as the statistical edge itself. This validates the user's original 1-minute-entry requirement rather than dismissing it, even though the full backtest couldn't be run at that granularity.

## Limitations
- **Sample size**: 89 days total, ~31 days held out for the only genuine out-of-sample test. Enough to catch gross overfitting, not enough to certify a durable edge.
- **No transaction costs modeled** (spread/commission on two legs, plus the bid/ask cost of maintaining a hedge ratio). At sub-0.1%-per-trade average returns, real costs would likely erase what edge is shown here.
- **Entries execute at the 15-min bar's close, not a full 1-min backtest** -- see the dedicated section above for the sample-based slippage measurement and why this matters more than it might sound.
- **Two instruments, one relationship, one 3-month window.** Not tested across other pairs, regimes, or longer history.
- **The regime filter (variance-ratio test) and the rolling/EWMA beta from v4.0 do not compose cleanly** -- a time-varying beta injects enough medium-frequency variance into the spread that the VR test calibrated for a static beta almost never passes. v5.0 uses an in-sample-fit STATIC beta instead, deliberately not carrying the rolling-beta experiment forward, since it underperformed even in isolation on this data.
