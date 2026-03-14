"""Exit condition logic for the funding rate strategy."""
from __future__ import annotations

from typing import Dict, Optional


class ExitManager:
    def check_exit_conditions(
        self,
        position: Dict,
        current_price: float,
        current_funding_rate: float,
        stop_loss_pct: float,
        neutral_rate_threshold: float,
        max_hold_periods: Optional[int] = None,
    ) -> Optional[str]:
        """
        Checks if any exit condition is met for a single position.
        Returns the reason for exit or None.
        """
        entry_price = position.get("entry_price", 0.0)
        if current_price <= 0 or entry_price <= 0:
            return None

        pnl_pct = (current_price - entry_price) / entry_price
        if pnl_pct <= stop_loss_pct:
            return "stop_loss"

        if current_funding_rate >= neutral_rate_threshold:
            return "funding_neutral"

        if max_hold_periods is not None and position.get("funding_periods_held", 0) >= max_hold_periods:
            return "max_hold"

        return None

    def check_stop_loss_only(
        self,
        position: Dict,
        current_price: float,
        stop_loss_pct: float,
    ) -> bool:
        entry_price = position.get("entry_price", 0.0)
        if current_price <= 0 or entry_price <= 0:
            return False
        pnl_pct = (current_price - entry_price) / entry_price
        return pnl_pct <= stop_loss_pct

    def close_position(self, state: Dict, symbol: str, exit_price: float, reason: str) -> Dict:
        """Updates the state by closing a position and calculating realized PnL."""
        positions = state.get("open_positions", {})
        position = positions.get(symbol)
        if not position:
            return state

        entry_price = position.get("entry_price", 0.0)
        size = position.get("size", 0.0)
        pnl = (exit_price - entry_price) * size

        state["realized_pnl"] = state.get("realized_pnl", 0.0) + pnl
        state["equity"] = state.get("equity", 0.0) + pnl

        position["exit_reason"] = reason
        position["exit_price"] = exit_price

        import datetime as dt

        position["exit_timestamp"] = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

        positions.pop(symbol, None)
        return state
