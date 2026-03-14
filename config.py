"""Strategy configuration parameters for the crypto funding harvester."""

# -- STRATEGY PARAMETERS --
TARGET_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
SECONDARY_SYMBOLS = ["AVAXUSDT", "DOGEUSDT", "LINKUSDT"]
ENTRY_FUNDING_RATE_THRESHOLD = -0.0001  # -0.01%
STOP_LOSS_PERCENTAGE = -0.03            # -3%
NEUTRAL_FUNDING_RATE_THRESHOLD = 0.0000 # 0.00%
MAX_HOLD_PERIODS = 3                    # 3 * 8h = 24h

# -- POSITION SIZING --
PORTFOLIO_RISK_BUDGET_PER_COIN = 0.15  # 15% of portfolio
MAX_LEVERAGE = 2.0
SCALING_MULTIPLIERS = {
    -0.0001: 1.0,  # -0.01% -> 1x base size
    -0.0005: 1.5,  # -0.05% -> 1.5x base size
    -0.0010: 2.0,  # -0.10% -> 2x base size (max)
}

# -- PAPER TRADING --
INITIAL_EQUITY = 10000.0

# -- STATE --
STATE_FILE_PATH = "state/strategy_state.json"
