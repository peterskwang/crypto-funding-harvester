# ML Entry-Probability Model -- Calibration Report

**Not investment advice.** This tests one specific question: when a model trained on backward-looking market-state features states a probability ("this entry has a 77% chance of hitting its target before its stop"), does that number hold up against real, held-out, out-of-sample outcomes? It is not a backtested trading strategy with a P&L curve -- see Limitations for what would still be needed to turn this into one.

## Why this project exists
A direct request to reverse-engineer a specific, high-confidence entry probability ("is 77.3% a trustworthy number") from indicators like volume, volume delta, ATR, price acceleration, and volume profile -- the 77.3% was an illustrative example in the original ask, not a target to hit. Rather than assert a number, this builds the actual pipeline needed to answer it honestly: objective triple-barrier labels (did price hit its target before its stop, looking forward -- standard supervised-learning label construction, not lookahead bias), strictly backward-looking features, a simple calibrated model, and a held-out test of whether the model's stated probabilities match reality. Run across three assets from two different classes (BTC, EURUSD, GBPUSD) so the finding isn't a one-asset artifact.

## Methodology
- **Labels (triple barrier):** for each bar, walk forward up to 16 bars (~4 hours at 15-min bars). Label = 1 if price hits 1.5x ATR profit target before 1.0x ATR stop-loss and before time runs out, else 0. Long and short candidates are labeled separately at every bar.
- **Features (strictly backward-looking):** volume_zscore, volume_delta_norm, atr_pct, price_accel, surge_ratio, dist_from_poc_pct -- volume z-score vs rolling mean, a Chaikin-style volume-delta proxy, ATR as a % of price, price acceleration (discrete 2nd derivative), a range-surge ratio, and distance from an approximate volume-profile point of control. None of these can see past the candidate bar.
- **Model:** plain logistic regression (L2=0.01) per asset per direction (6 models total), chosen deliberately over anything fancier -- a few thousand labeled examples and six features is not enough data to justify gradient boosting or a neural net without just overfitting the noise in one data window.
- **Split:** in-sample (fit standardization and train weights) through each asset's own split date, out-of-sample after that (scored once, never refit).
- **BTCUSD volume:** ~4.2% of raw 5-min bars had a corrupted `volume` field (a clean gap in the distribution separates real values, topping out ~1.7B, from glitch values starting ~14B) -- OHLC was unaffected; repaired with the local median of nearby clean bars before any feature or label was computed.
- **EURUSD/GBPUSD volume:** broker tick-count, not true traded volume (FX spot has no centralized tape) -- directionally useful as an activity proxy, but on a different footing than BTC's coin-volume. No corrupted-value defect was found in this data, so no cleaning was applied.

## BTCUSD
- **Data:** 8544 15-min bars, 2026-04-21 to 2026-07-18. Split at 2026-06-20 (in-sample before, out-of-sample after).

### BTCUSD -- Long entries
- IS rows: 5664 (base win rate 34.1%) | OOS rows: 2768 (base win rate 36.7%)
- OOS AUC: 0.567 (0.5 = no better than chance) | OOS Brier: 0.2313 (naive base-rate Brier: 0.2331)

| Predicted bucket | n (OOS) | Predicted mean | Actual hit rate |
|---|---|---|---|
| 0-30% | 623 | 25.6% | 30.2% |
| 30-40% | 1928 | 35.1% | 37.7% |
| 40-50% | 214 | 41.6% | 47.2% |
| 50-60% | 3 | 52.5% | 66.7% |
| 60-70% | 0 | -- | -- (no predictions landed here) |
| 70-80% | 0 | -- | -- (no predictions landed here) |
| 80-100% | 0 | -- | -- (no predictions landed here) |

### BTCUSD -- Short entries
- IS rows: 5664 (base win rate 40.4%) | OOS rows: 2768 (base win rate 36.7%)
- OOS AUC: 0.497 (0.5 = no better than chance) | OOS Brier: 0.2354 (naive base-rate Brier: 0.2337)

| Predicted bucket | n (OOS) | Predicted mean | Actual hit rate |
|---|---|---|---|
| 0-30% | 0 | -- | -- (no predictions landed here) |
| 30-40% | 1364 | 38.7% | 36.3% |
| 40-50% | 1388 | 42.0% | 37.6% |
| 50-60% | 16 | 53.8% | 0.0% |
| 60-70% | 0 | -- | -- (no predictions landed here) |
| 70-80% | 0 | -- | -- (no predictions landed here) |
| 80-100% | 0 | -- | -- (no predictions landed here) |

## EURUSD
- **Data:** 12192 15-min bars, 2026-01-18 to 2026-07-16. Split at 2026-05-15 (in-sample before, out-of-sample after).

### EURUSD -- Long entries
- IS rows: 7776 (base win rate 36.6%) | OOS rows: 4304 (base win rate 33.6%)
- OOS AUC: 0.588 (0.5 = no better than chance) | OOS Brier: 0.2226 (naive base-rate Brier: 0.2240)

| Predicted bucket | n (OOS) | Predicted mean | Actual hit rate |
|---|---|---|---|
| 0-30% | 1 | 29.1% | 0.0% |
| 30-40% | 4092 | 37.1% | 33.5% |
| 40-50% | 210 | 41.4% | 36.7% |
| 50-60% | 1 | 50.3% | 0.0% |
| 60-70% | 0 | -- | -- (no predictions landed here) |
| 70-80% | 0 | -- | -- (no predictions landed here) |
| 80-100% | 0 | -- | -- (no predictions landed here) |

### EURUSD -- Short entries
- IS rows: 7776 (base win rate 38.4%) | OOS rows: 4304 (base win rate 40.6%)
- OOS AUC: 0.528 (0.5 = no better than chance) | OOS Brier: 0.2403 (naive base-rate Brier: 0.2416)

| Predicted bucket | n (OOS) | Predicted mean | Actual hit rate |
|---|---|---|---|
| 0-30% | 13 | 28.5% | 0.0% |
| 30-40% | 1886 | 38.0% | 37.9% |
| 40-50% | 2405 | 41.5% | 42.9% |
| 50-60% | 0 | -- | -- (no predictions landed here) |
| 60-70% | 0 | -- | -- (no predictions landed here) |
| 70-80% | 0 | -- | -- (no predictions landed here) |
| 80-100% | 0 | -- | -- (no predictions landed here) |

## GBPUSD
- **Data:** 12189 15-min bars, 2026-01-18 to 2026-07-16. Split at 2026-05-15 (in-sample before, out-of-sample after).

### GBPUSD -- Long entries
- IS rows: 7715 (base win rate 35.9%) | OOS rows: 4303 (base win rate 33.6%)
- OOS AUC: 0.543 (0.5 = no better than chance) | OOS Brier: 0.2231 (naive base-rate Brier: 0.2236)

| Predicted bucket | n (OOS) | Predicted mean | Actual hit rate |
|---|---|---|---|
| 0-30% | 1 | 28.0% | 0.0% |
| 30-40% | 4069 | 35.5% | 33.3% |
| 40-50% | 219 | 42.3% | 38.8% |
| 50-60% | 9 | 53.3% | 11.1% |
| 60-70% | 5 | 62.9% | 40.0% |
| 70-80% | 0 | -- | -- (no predictions landed here) |
| 80-100% | 0 | -- | -- (no predictions landed here) |

### GBPUSD -- Short entries
- IS rows: 7715 (base win rate 39.3%) | OOS rows: 4303 (base win rate 41.8%)
- OOS AUC: 0.534 (0.5 = no better than chance) | OOS Brier: 0.2423 (naive base-rate Brier: 0.2438)

| Predicted bucket | n (OOS) | Predicted mean | Actual hit rate |
|---|---|---|---|
| 0-30% | 13 | 29.2% | 38.5% |
| 30-40% | 1176 | 37.5% | 39.4% |
| 40-50% | 3114 | 42.6% | 42.7% |
| 50-60% | 0 | -- | -- (no predictions landed here) |
| 60-70% | 0 | -- | -- (no predictions landed here) |
| 70-80% | 0 | -- | -- (no predictions landed here) |
| 80-100% | 0 | -- | -- (no predictions landed here) |

## Cross-asset summary
| Asset | Direction | OOS n | OOS AUC | Predicted range |
|---|---|---|---|---|
| BTCUSD | long | 2768 | 0.567 | 7-54% |
| BTCUSD | short | 2768 | 0.497 | 36-59% |
| EURUSD | long | 4304 | 0.588 | 29-50% |
| EURUSD | short | 4304 | 0.528 | 27-48% |
| GBPUSD | long | 4303 | 0.543 | 28-67% |
| GBPUSD | short | 4303 | 0.534 | 27-47% |

## Honest verdict
**Across all three assets, both directions, and 22750 total out-of-sample predictions, the model essentially never predicts anywhere near 77%.** Only one asset/direction combination (GBPUSD long) ever produced a prediction at or above 60% confidence at all, and even there it was 5 rows out of 4303 -- and those 5 rows' actual hit rate (40%) badly missed their own predicted average (62.9%), the signature of a small, noisy bucket rather than real high confidence. That spike traces to a disclosed limitation (FX tick volume near zero during illiquid sessions can blow up the volume z-score feature from a near-zero baseline standard deviation), not a genuine high-confidence signal. Every other asset/direction never predicted above 60% at all. Predicted probabilities stay clustered in a narrow band near each asset's own base rate, because that's genuinely where the edge in these six features tops out. A well-calibrated model doesn't manufacture confidence it can't back up -- and that restraint is itself the answer to the original question: on this feature set, a stated 77.3% would not be trustworthy on any of these assets, because no honestly-validated model trained on this data gets anywhere close to that number in any way that survives scrutiny.

**BTCUSD long**: OOS AUC 0.567 (real, modest edge) | **BTCUSD short**: OOS AUC 0.497 (no real edge) | **EURUSD long**: OOS AUC 0.588 (real, modest edge) | **EURUSD short**: OOS AUC 0.528 (weak/inconclusive) | **GBPUSD long**: OOS AUC 0.543 (weak/inconclusive) | **GBPUSD short**: OOS AUC 0.534 (weak/inconclusive)

The pattern that emerges: whatever structure these six features capture is asset- and direction-specific, not a universal edge. It shows up unevenly (strongest in the asset with the strongest realized trend over its own out-of-sample window) rather than consistently across every market and direction -- which is itself informative. A feature set with a real, general edge would be expected to show at least a consistent sign and magnitude across uncorrelated assets; this one doesn't.

## What this means for the original 5%/month goal
This was framed as a different kind of test than the prior two projects (FX cointegration, crypto trend-following) -- not "does this make money" but "can a stated entry probability be trusted." The honest answer generalizes the same way the other two did, and generalizes further now across three assets: real, measurable structure sometimes exists, but it is nowhere near strong enough, nor consistent enough, to support a high-confidence, frequent-entry claim like "77.3% probability." A well-built, honestly-validated model on this feature set reliably tops out in the high-40s to low-50s% predicted confidence across every asset and direction tested, not 77.3% -- the one nominal excursion to 67.4% (5 rows, GBPUSD long) is noise from a disclosed data limitation, not a real high-confidence prediction.

## Limitations
- **Single historical window per asset**, not multiple market regimes -- BTC covers ~89 days, EURUSD/GBPUSD ~180 days, all from roughly the same 2026 calendar period.
- **This is a labeling/calibration study, not a backtested strategy.** No transaction costs, slippage, execution latency, or position sizing are modeled; turning a well-calibrated probability into a real P&L curve is a separate step.
- **Volume delta and volume profile are OHLCV approximations**, not real tick-level order flow on any of the three assets.
- **FX weekend gaps aren't calendar-aware**: bar-count-based lookback windows (volume z-score, ATR, volume profile) treat Friday's last bar and Sunday's first bar as adjacent, same as every other bar-count indicator in this codebase -- a real approximation, not unique to this project.
- **FX tick volume can be near-zero during illiquid sessions**, which can produce extreme volume z-scores from a near-zero baseline standard deviation (seen on GBPUSD) -- a real property of the data, not a defect, but it means that feature can be spiky in a way BTC's continuous 24/7 volume mostly isn't.
- **Intrabar barrier-touch ordering is inferred**, not observed: when a single forward bar's range touches both the profit and stop levels, the true path within that bar is unknown from OHLC alone; a same-bar heuristic (nearest to open resolves first) is used and disclosed in `labels.py`.
- **~4.2% of raw BTC volume data required repair** due to an upstream feed defect (see Methodology) -- repaired via local median substitution, not dropped, since OHLC on those bars was clean and dropping bars would break time continuity.
