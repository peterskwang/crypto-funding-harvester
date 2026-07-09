from unittest import mock

from pre_ipo_screener.data.polygon_client import PolygonClient
from pre_ipo_screener.screener.universe import build_upcoming_universe, normalize_ipo_record

REAL_IPO = {
    "ticker": "ACRB",
    "issuer_name": "Acme Robotics Inc.",
    "listing_date": "2026-07-20",
    "security_type": "CS",
    "primary_exchange": "XNAS",
    "min_offer_price": 18,
    "max_offer_price": 21,
    "shares_outstanding": 10_000_000,
}

ETF_NOISE = {
    "ticker": "GXRB",
    "issuer_name": "Global X Robotics ETF",
    "listing_date": "2026-07-20",
    "security_type": "ETF",
}

SPAC_UNIT_NOISE = {
    "ticker": "MRCOU",
    "issuer_name": "Mercator Acquisition Corp. Units",
    "listing_date": "2026-07-20",
    "security_type": "UNIT",
}

TRUST_NOISE = {
    "ticker": "EXPA",
    "issuer_name": "Exchange Place Advisors Trust",
    "listing_date": "2026-07-20",
    "security_type": "CS",
}


def test_normalize_ipo_record_keeps_real_operating_company():
    normalized = normalize_ipo_record(REAL_IPO)
    assert normalized is not None
    assert normalized["ticker"] == "ACRB"
    assert normalized["total_offer_size"] == 10_000_000 * 21


def test_normalize_ipo_record_drops_etf():
    assert normalize_ipo_record(ETF_NOISE) is None


def test_normalize_ipo_record_drops_spac_units():
    assert normalize_ipo_record(SPAC_UNIT_NOISE) is None


def test_normalize_ipo_record_drops_trust():
    assert normalize_ipo_record(TRUST_NOISE) is None


def test_build_upcoming_universe_filters_noise():
    client = mock.Mock(spec=PolygonClient)
    client.get_ipos.return_value = [REAL_IPO, ETF_NOISE, SPAC_UNIT_NOISE, TRUST_NOISE]

    candidates = build_upcoming_universe(client)

    assert len(candidates) == 1
    assert candidates[0]["ticker"] == "ACRB"
