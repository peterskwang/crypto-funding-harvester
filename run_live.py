"""One-shot runner for the crypto funding rate harvesting strategy."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Dict

import config
from execution.binance_client import BinanceFuturesClient
from strategy.exit_manager import ExitManager
from strategy.funding_scanner import FundingScanner
from strategy.position_manager import PositionManager
from utils.logger import configure_logging
from utils.state import load_state, save_state


def _combine_symbols() -> list[str]:
    ordered = config.TARGET_SYMBOLS + config.SECONDARY_SYMBOLS
    # preserve order but remove duplicates
    seen = set()
    unique = []
    for symbol in ordered:
        if symbol not in seen:
            seen.add(symbol)
            unique.append(symbol)
    return unique


def _ensure_equity(state: Dict) -> None:
    if state.get("equity", 0.0) <= 0:
        state["equity"] = config.INITIAL_EQUITY


def main() -> None:
    logger = configure_logging()
    logger.info("Starting funding rate harvesting run")

    state = load_state(config.STATE_FILE_PATH)
    _ensure_equity(state)

    client = BinanceFuturesClient()
    scanner = FundingScanner(client, _combine_symbols())
    position_manager = PositionManager()
    exit_manager = ExitManager()

    # Entry cycle
    try:
        opportunities = scanner.find_opportunities(config.ENTRY_FUNDING_RATE_THRESHOLD)
    except Exception as exc:  # pragma: no cover - network guard
        logger.exception("Failed to scan funding rates: %s", exc)
        opportunities = {}

    for symbol, funding_rate in opportunities.items():
        if symbol in state.get("open_positions", {}):
            continue
        try:
            price = client.get_latest_price(symbol)
        except Exception as exc:  # pragma: no cover - network guard
            logger.warning("Could not fetch price for %s: %s", symbol, exc)
            continue

        size = position_manager.calculate_position_size(
            equity=state["equity"],
            risk_budget=config.PORTFOLIO_RISK_BUDGET_PER_COIN,
            leverage=config.MAX_LEVERAGE,
            price=price,
            funding_rate=funding_rate,
            multipliers=config.SCALING_MULTIPLIERS,
        )
        if size <= 0:
            continue

        state = position_manager.open_position(state, symbol, size, price, funding_rate)
        logger.info("Opened paper position %s | size=%.6f @ %.2f | funding=%.5f", symbol, size, price, funding_rate)

    # Exit + funding cycle
    open_positions = state.get("open_positions", {})
    symbols = list(open_positions.keys())
    funding_rates: Dict[str, float] = {}
    if symbols:
        try:
            funding_rates = client.get_funding_rates(symbols)
        except Exception as exc:  # pragma: no cover - network guard
            logger.warning("Failed to refresh funding rates for open positions: %s", exc)

    for symbol in list(open_positions.keys()):
        position = open_positions[symbol]
        try:
            current_price = client.get_latest_price(symbol)
        except Exception as exc:  # pragma: no cover
            logger.warning("Could not fetch price for %s: %s", symbol, exc)
            continue

        current_rate = funding_rates.get(symbol, position.get("entry_funding_rate", 0.0))
        reason = exit_manager.check_exit_conditions(
            position,
            current_price,
            current_rate,
            config.STOP_LOSS_PERCENTAGE,
            config.NEUTRAL_FUNDING_RATE_THRESHOLD,
            config.MAX_HOLD_PERIODS,
        )
        if reason:
            state = exit_manager.close_position(state, symbol, current_price, reason)
            logger.info("Closed %s due to %s @ %.2f", symbol, reason, current_price)
            continue

        funding_payment = position.get("size", 0.0) * current_price * current_rate
        timestamp = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        state.setdefault("funding_history", []).append(
            {
                "timestamp": timestamp,
                "symbol": symbol,
                "rate": current_rate,
                "amount_usd": round(funding_payment, 4),
            }
        )
        state["realized_pnl"] = state.get("realized_pnl", 0.0) + funding_payment
        state["equity"] = state.get("equity", 0.0) + funding_payment
        position["funding_periods_held"] = position.get("funding_periods_held", 0) + 1
        logger.info(
            "Logged funding for %s | rate=%.5f amount=%.2f",
            symbol,
            current_rate,
            funding_payment,
        )

    # Stop-loss only cycle
    for symbol in list(open_positions.keys()):
        position = open_positions[symbol]
        try:
            current_price = client.get_latest_price(symbol)
        except Exception as exc:  # pragma: no cover
            logger.warning("Stop-loss price fetch failed for %s: %s", symbol, exc)
            continue

        if exit_manager.check_stop_loss_only(position, current_price, config.STOP_LOSS_PERCENTAGE):
            state = exit_manager.close_position(state, symbol, current_price, "stop_loss")
            logger.info("Emergency stop-loss closed %s @ %.2f", symbol, current_price)

    save_state(config.STATE_FILE_PATH, state)
    logger.info("Run complete. Equity=%.2f | Open positions=%d", state.get("equity", 0.0), len(state.get("open_positions", {})))


if __name__ == "__main__":
    main()
