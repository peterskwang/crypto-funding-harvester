"""Position sizing and management helpers."""
from __future__ import annotations

import datetime as dt
from typing import Dict


class PositionManager:
    def calculate_position_size(
        self,
        equity: float,
        risk_budget: float,
        leverage: float,
        price: float,
        funding_rate: float,
        multipliers: Dict[float, float],
    ) -> float:
        """
        Calculates the position size in base currency (e.g., BTC).
        """
        if equity <= 0 or price <= 0:
            return 0.0

        notional_budget = equity * max(risk_budget, 0)
        notional_budget *= max(min(leverage, 10.0), 0.0)

        multiplier = 0.0
        sorted_thresholds = sorted(multipliers.items())
        if sorted_thresholds:
            # default to the least aggressive multiplier (closest to zero threshold)
            multiplier = sorted_thresholds[-1][1]
            for threshold, mult in sorted_thresholds:
                if funding_rate <= threshold:
                    multiplier = mult
                    break

        position_notional = notional_budget * multiplier
        if position_notional <= 0:
            return 0.0

        size = position_notional / price
        return round(size, 6)

    def open_position(
        self,
        state: Dict,
        symbol: str,
        size: float,
        price: float,
        funding_rate: float,
    ) -> Dict:
        """Updates the state dictionary with a new paper-traded position."""
        if size <= 0:
            return state

        positions = state.setdefault("open_positions", {})
        if symbol in positions:
            return state

        positions[symbol] = {
            "entry_price": price,
            "size": size,
            "entry_funding_rate": funding_rate,
            "entry_timestamp": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "funding_periods_held": 0,
        }
        return state
