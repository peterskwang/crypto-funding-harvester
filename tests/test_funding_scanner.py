from unittest import mock

import pytest

from execution.binance_client import BinanceFuturesClient
from strategy.funding_scanner import FundingScanner


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise ValueError("error")

    def json(self):
        return self._payload


@mock.patch("requests.Session.get")
def test_get_funding_rates_parses_response(mock_get):
    mock_get.return_value = DummyResponse({"lastFundingRate": "-0.0003"})
    client = BinanceFuturesClient()
    rates = client.get_funding_rates(["BTCUSDT"])
    assert rates["BTCUSDT"] == pytest.approx(-0.0003)


def test_scanner_identifies_opportunities():
    client = mock.Mock(spec=BinanceFuturesClient)
    client.get_funding_rates.return_value = {"BTCUSDT": -0.0002, "ETHUSDT": 0.0001}
    scanner = FundingScanner(client, ["BTCUSDT", "ETHUSDT"])

    opportunities = scanner.find_opportunities(-0.0001)

    assert opportunities == {"BTCUSDT": -0.0002}


def test_scanner_ignores_symbols_above_threshold():
    client = mock.Mock(spec=BinanceFuturesClient)
    client.get_funding_rates.return_value = {"SOLUSDT": 0.0}
    scanner = FundingScanner(client, ["SOLUSDT"])

    opportunities = scanner.find_opportunities(-0.0001)

    assert opportunities == {}
