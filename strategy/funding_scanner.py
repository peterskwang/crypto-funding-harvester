"""Logic to scan Binance funding rates for entry opportunities."""
from __future__ import annotations

from typing import Dict, List

from execution.binance_client import BinanceFuturesClient


class FundingScanner:
    def __init__(self, client: BinanceFuturesClient, symbols: List[str]):
        self.client = client
        self.symbols = symbols

    def find_opportunities(self, entry_threshold: float) -> Dict[str, float]:
        """
        Scans for symbols with funding rates below the entry threshold.
        Returns a dictionary of {symbol: funding_rate}.
        """
        funding_rates = self.client.get_funding_rates(self.symbols)
        opportunities = {
            symbol: rate
            for symbol, rate in funding_rates.items()
            if rate is not None and rate <= entry_threshold
        }
        return opportunities
