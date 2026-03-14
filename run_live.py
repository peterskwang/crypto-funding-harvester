"""One-shot runner for the crypto funding rate harvesting strategy."""
from __future__ import annotations

import datetime as dt
from typing import Dict, List

import config
from execution.binance_client import BinanceFuturesClient
from strategy.exit_manager import ExitManager
from strategy.funding_scanner import FundingScanner
from strategy.position_manager import PositionManager
from utils.logger import configure_logging
from utils.state import load_state, save_state


def _combine_symbols() -> List[str]:
    ordered = config.TARGET_SYMBOLS + config.SECONDARY_SYMBOLS
    seen = set()
    unique: List[str] = []
    for symbol in ordered:
        if symbol not in seen:
            seen.add(symbol)
            unique.append(symbol)
    return unique


def _ensure_state_defaults(state: Dict) -> None:
    state.setdefault("equity", config.INITIAL_EQUITY)
    state.setdefault("realized_pnl", 0.0)
    state.setdefault("open_positions", {})
    state.setdefault("funding_history", [])
    if state["equity"] <= 0:
        state["equity"] = config.INITIAL_EQUITY


def _process_open_positions(
    state: Dict,
    client: BinanceFuturesClient,
    exit_manager: ExitManager,
    logger,
) -> None:
    open_positions = state.get("open_positions", {})
    if not open_positions:
        return

    symbols = list(open_positions.keys())
    funding_rates: Dict[str, float] = {}
    try:
        funding_rates = client.get_funding_rates(symbols)
    except Exception as exc:  # pragma: no cover - safety net for live runs
        logger.warning("Failed to refresh funding rates for open positions: %s", exc)

    for symbol in list(open_positions.keys()):
        position = open_positions.get(symbol)
        if not position:
            continue
        try:
            current_price = client.get_latest_price(symbol)
        except Exception as exc:  # pragma: no cover - network guard
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
            exit_manager.close_position(state, symbol, current_price, reason)
            logger.info("Closed %s due to %s @ %.2f", symbol, reason, current_price)
            continue

        funding_payment = position.get("size", 0.0) * current_price * current_rate
        timestamp = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        state["funding_history"].append(
            {
                "timestamp": timestamp,
                "symbol": symbol,
                "rate": current_rate,
                "amount_usd": round(funding_payment, 4),
            }
        )
        state["realized_pnl"] += funding_payment
        state["equity"] += funding_payment
        position["funding_periods_held"] = position.get("funding_periods_held", 0) + 1
        logger.info(
            "Logged funding for %s | rate=%.5f amount=%.2f",
            symbol,
            current_rate,
            funding_payment,
        )

    # Emergency stop-loss sweep in case price moved after funding collection
    for symbol in list(open_positions.keys()):
        position = open_positions.get(symbol)
        if not position:
            continue
        try:
            current_price = client.get_latest_price(symbol)
        except Exception as exc:  # pragma: no cover - network guard
            logger.warning("Stop-loss price fetch failed for %s: %s", symbol, exc)
            continue
        if exit_manager.check_stop_loss_only(position, current_price, config.STOP_LOSS_PERCENTAGE):
            exit_manager.close_position(state, symbol, current_price, "stop_loss")
            logger.info("Emergency stop-loss closed %s @ %.2f", symbol, current_price)


def _scan_and_open_positions(
    state: Dict,
    client: BinanceFuturesClient,
    position_manager: PositionManager,
    scanner: FundingScanner,
    logger,
) -> None:
    try:
        opportunities = scanner.find_opportunities(config.ENTRY_FUNDING_RATE_THRESHOLD)
    except Exception as exc:  # pragma: no cover - network guard
        logger.exception("Failed to scan funding rates: %s", exc)
        return

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

        position_manager.open_position(state, symbol, size, price, funding_rate)
        logger.info(
            "Opened paper position %s | size=%.6f @ %.2f | funding=%.5f",
            symbol,
            size,
            price,
            funding_rate,
        )


def main() -> None:
    logger = configure_logging()
    logger.info("Starting funding rate harvesting run")

    state = load_state(config.STATE_FILE_PATH)
    _ensure_state_defaults(state)

    client = BinanceFuturesClient()
    scanner = FundingScanner(client, _combine_symbols())
    position_manager = PositionManager()
    exit_manager = ExitManager()

    _process_open_positions(state, client, exit_manager, logger)
    _scan_and_open_positions(state, client, position_manager, scanner, logger)

    save_state(config.STATE_FILE_PATH, state)
    logger.info(
        "Run complete. Equity=%.2f | Open positions=%d",
        state.get("equity", 0.0),
        len(state.get("open_positions", {})),
    )


if __name__ == "__main__":
    main()
