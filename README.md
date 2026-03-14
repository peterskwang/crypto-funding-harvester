# Crypto Funding Rate Harvester

Paper-trading bot that scans Binance USDT-M perpetuals for negative funding rates and opens long positions to collect the next funding payment. Designed as a one-shot script suitable for cron-driven executions.

## Features
- Targets major & secondary pairs: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, AVAXUSDT, DOGEUSDT, LINKUSDT
- Paper trading only — no credentials or live order routing
- JSON state tracking for equity, PnL, open positions, and funding receipts
- Funding history logs every payment with timestamp, symbol, rate, and USD amount
- Built-in stop-loss (-3%), neutral funding exit, and maximum hold period (3 funding cycles)
- One-shot `run_live.py` runner that can be invoked every 4–8 hours via cron

## Getting Started
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the Strategy
```bash
python run_live.py
```
The script will:
1. Load configuration and paper-trading state
2. Scan all configured symbols for funding rates below -0.01%
3. Open paper positions sized by risk budget, leverage cap, and funding-rate-based multipliers
4. Manage open positions by applying exit rules, logging funding receipts, and enforcing a stop-loss-only pass
5. Save updated state back to `state/strategy_state.json`

## Tests
```bash
pytest
```

## Configuration
Edit `config.py` to adjust thresholds, leverage, or allocation parameters. The default state file can be reset by replacing `state/strategy_state.json` with the template contents from the brief.
