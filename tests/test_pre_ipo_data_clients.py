import os
from unittest import mock

import pytest

from pre_ipo_screener.data.client_factory import NoDataSourceConfigured, get_client
from pre_ipo_screener.data.fmp_client import FMPAuthError, FMPClient
from pre_ipo_screener.data.polygon_client import PolygonClient


class DummyResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise ValueError("error")

    def json(self):
        return self._payload


def test_fmp_client_requires_api_key():
    client = FMPClient(api_key=None)
    with pytest.raises(FMPAuthError):
        client.get_ipos()


@mock.patch("requests.Session.get")
def test_fmp_get_ipos_normalizes_to_polygon_shape(mock_get):
    mock_get.return_value = DummyResponse(
        [
            {
                "symbol": "ACRB",
                "company": "Acme Robotics Inc.",
                "date": "2026-07-20",
                "exchange": "NASDAQ",
                "priceRange": "18.00 - 21.00",
                "shares": 10_000_000,
                "marketCap": 210_000_000,
            }
        ]
    )
    client = FMPClient(api_key="fake-key")

    records = client.get_ipos(listing_date_gte="2026-07-01", listing_date_lte="2026-08-01")

    assert len(records) == 1
    record = records[0]
    assert record["ticker"] == "ACRB"
    assert record["issuer_name"] == "Acme Robotics Inc."
    assert record["listing_date"] == "2026-07-20"
    assert record["primary_exchange"] == "NASDAQ"
    assert record["min_offer_price"] == 18.0
    assert record["max_offer_price"] == 21.0
    assert record["total_offer_size"] == 210_000_000


@mock.patch("requests.Session.get")
def test_fmp_get_daily_bars_reverses_to_ascending(mock_get):
    mock_get.return_value = DummyResponse(
        [
            {"date": "2026-07-10", "open": 11.0, "close": 12.0},
            {"date": "2026-07-09", "open": 10.0, "close": 11.0},
        ]
    )
    client = FMPClient(api_key="fake-key")

    bars = client.get_daily_bars("ACRB", "2026-07-09", "2026-07-10")

    assert [b["date"] for b in bars] == ["2026-07-09", "2026-07-10"]
    assert bars[0]["o"] == 10.0
    assert bars[0]["c"] == 11.0


@mock.patch("requests.Session.get")
def test_fmp_get_ticker_details_extracts_sector(mock_get):
    mock_get.return_value = DummyResponse([{"sector": "Technology", "marketCap": 500_000_000}])
    client = FMPClient(api_key="fake-key")

    details = client.get_ticker_details("ACRB")

    assert details["sector"] == "Technology"


def test_client_factory_prefers_polygon_when_both_set(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "poly-key")
    monkeypatch.setenv("FMP_API_KEY", "fmp-key")

    client = get_client()

    assert isinstance(client, PolygonClient)


def test_client_factory_falls_back_to_fmp(monkeypatch):
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    monkeypatch.setenv("FMP_API_KEY", "fmp-key")

    client = get_client()

    assert isinstance(client, FMPClient)


def test_client_factory_raises_when_neither_configured(monkeypatch):
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    monkeypatch.delenv("FMP_API_KEY", raising=False)

    with pytest.raises(NoDataSourceConfigured):
        get_client()
