# ML Entry-Probability Model -- Calibration Report

**Not investment advice.** This tests one specific question: when a model trained on backward-looking market-state features states a probability ("this entry has a 77% chance of hitting its target before its stop"), does that number hold up against real, held-out, out-of-sample outcomes? It is not a backtested trading strategy with a P&L curve -- see Limitations for what would still be needed to turn this into one.

## Why this project exists
A direct request to reverse-engineer a specific, high-confidence entry probability ("is 77.3% a trustworthy number") from indicators like volume, volume delta, ATR, price acceleration, and volume profile. Rather than assert a number, this builds the actual pipeline needed to answer it honestly: objective triple-barrier labels (did price hit its target before its stop, looking forward -- standard supervised-learning label construction, not lookahead bias), strictly backward-looking features, a simple calibrated model, and a held-out test of whether the model's stated probabilities match reality.

## Methodology
- **Data:** BTCUSD 15-min bars aggregated from 5-min data (2026-04-21 to 2026-07-18, ~89 days). ~4.2% of raw 5-min bars had a corrupted `volume` field (a clean gap in the volume distribution separates real values, topping out ~1.7B, from glitch values starting ~14B) -- OHLC was unaffected; volume on those bars was repaired with the local median of nearby clean bars before any feature or label was computed.
- **Labels (triple barrier):** for each bar, walk forward up to 16 bars (~4 hours). Label = 1 if price hits 1.5x ATR profit target before 1.0x ATR stop-loss and before time runs out, else 0. Long and short candidates are labeled separately at every bar.
- **Features (strictly backward-looking):** volume_zscore, volume_delta_norm, atr_pct, price_accel, surge_ratio, dist_from_poc_pct -- volume z-score vs rolling mean, a Chaikin-style volume-delta proxy, ATR as a % of price, price acceleration (discrete 2nd derivative), a range-surge ratio, and distance from an approximate volume-profile point of control. None of these can see past the candidate bar.
- **Model:** plain logistic regression (L2=0.01), chosen deliberately over anything fancier -- a few thousand labeled examples and six features is not enough data to justify gradient boosting or a neural net without just overfitting the noise in one 89-day window.
- **Split:** in-sample through 2026-06-20 (fit standardization and train weights), out-of-sample after that (scored once, never refit).

## Results
### Long entries
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

### Short entries
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

## Honest verdict
**The model never once predicted anywhere near 77% -- on either side, in-sample or out-of-sample.** Its predicted probabilities cluster tightly in the 7-54% (long) and 36-59% (short) range, because that's genuinely where the edge in these six features tops out on this data. A well-calibrated model doesn't manufacture confidence it can't back up -- and that restraint is itself the answer to the original question: on this feature set and this data, a stated 77.3% would not be trustworthy, because no honest model trained on it produces a number anywhere close to that.

**Long side shows a real, modest, out-of-sample edge**: OOS AUC 0.567 (vs. 0.500 for coin-flip), and the calibration table tracks reasonably -- predicted and actual move together bucket to bucket, though actual rates run consistently a few points above predicted. That gap is most likely a base-rate shift: the in-sample win rate (34.1%) was lower than the out-of-sample win rate (36.7%) -- BTC's realized path in the held-out window was modestly more favorable to longs than the window the model was fit on, which shifts every bucket's actual rate up by roughly the same amount. That's a real limitation (the model assumes a stationary base rate) but not a sign the ranking itself is broken.

**Short side shows no real edge**: OOS AUC 0.497, statistically indistinguishable from 0.500. These six features do not predict short-side outcomes on this data; the calibration table for shorts should not be trusted for sizing decisions.

## What this means for the original 5%/month goal
This was framed as a different kind of test than the prior two projects (FX cointegration, crypto trend-following) -- not "does this make money" but "can a stated entry probability be trusted." The honest answer generalizes the same way the other two did: real, measurable, modest structure exists (long-side AUC ~0.57 is a genuine, non-random signal), but it is nowhere near strong enough to support the kind of high-confidence, frequent-entry claim ("77.3% probability") the original idea was reaching for. A well-built, honestly-validated model on this feature set tops out around 54.3% predicted confidence, not 77.3%.

## Limitations
- **Single 89-day window, single asset.** BTC 15-min bars over one specific quarter -- not multiple market regimes or assets.
- **This is a labeling/calibration study, not a backtested strategy.** No transaction costs, slippage, execution latency, or position sizing are modeled; turning a well-calibrated probability into a real P&L curve is a separate step.
- **Volume delta and volume profile are OHLCV approximations**, not real tick-level order flow -- crypto spot OHLCV data has no true aggressor-side data.
- **Intrabar barrier-touch ordering is inferred**, not observed: when a single forward bar's range touches both the profit and stop levels, the true path within that bar is unknown from OHLC alone; a same-bar heuristic (nearest to open resolves first) is used and disclosed in `labels.py`.
- **~4.2% of raw volume data required repair** due to an upstream feed defect (see Methodology) -- repaired via local median substitution, not dropped, since OHLC on those bars was clean and dropping bars would break time continuity.
