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

# Real numbered-SPAC-shell examples pulled from a live IPO calendar during
# validation that slipped past a plain "ACQUISITION CORP" substring check.
NUMBERED_SPAC_NOISE = [
    {"ticker": "IDAC", "issuer_name": "Iron Dome Acquisition I Corp.", "listing_date": "2026-07-06"},
    {"ticker": "MCAH", "issuer_name": "Mountain Crest Acquisition 6 Corp.", "listing_date": "2026-06-22"},
    {"ticker": "LEGO", "issuer_name": "Legato Merger Corp. IV", "listing_date": "2026-03-16"},
    {"ticker": "GIX9", "issuer_name": "GigCapital9 Corp.", "listing_date": "2026-03-19"},
    {"ticker": "CAES", "issuer_name": "Cantor Equity Partners Vii Inc.", "listing_date": "2026-06-17"},
    {"ticker": "RACC", "issuer_name": "Research Alliance Corporation III Class A", "listing_date": "2026-05-20"},
    {"ticker": "HCIC", "issuer_name": "Hennessy Capital Investment Corp. VIII", "listing_date": "2026-03-30"},
    {"ticker": "TRGS", "issuer_name": "TRG Latin America Acquisitions Corp. Class A", "listing_date": "2026-04-20"},
    {"ticker": "XSLL", "issuer_name": "Xsolla SPAC 1 Class A Ordinary Shares", "listing_date": "2026-03-18"},
]

# Legitimate operating companies that must survive the numbered-SPAC regexes
# despite superficially similar naming (Corp/Corporation/Holdings present).
LEGIT_LOOKALIKES = [
    {"ticker": "QNT", "issuer_name": "Quantinuum Inc. Class A Common Stock", "listing_date": "2026-06-04"},
    {"ticker": "CBRS", "issuer_name": "Cerebras Systems Inc.", "listing_date": "2026-05-14"},
    {"ticker": "HMH", "issuer_name": "HMH Holding Inc. Class A Common Stock", "listing_date": "2026-04-01"},
    {"ticker": "PAYP", "issuer_name": "PayPay Corporation", "listing_date": "2026-03-12"},
    {"ticker": "MAKO", "issuer_name": "Mako Mining Corp", "listing_date": "2026-03-30"},
]


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


def test_normalize_ipo_record_drops_numbered_spac_shells():
    for record in NUMBERED_SPAC_NOISE:
        assert normalize_ipo_record(record) is None, f"{record['issuer_name']} should have been filtered as noise"


def test_normalize_ipo_record_keeps_legit_lookalikes():
    for record in LEGIT_LOOKALIKES:
        normalized = normalize_ipo_record(record)
        assert normalized is not None, f"{record['issuer_name']} should NOT have been filtered"
        assert normalized["ticker"] == record["ticker"]


def test_build_upcoming_universe_filters_noise():
    client = mock.Mock(spec=PolygonClient)
    client.get_ipos.return_value = [REAL_IPO, ETF_NOISE, SPAC_UNIT_NOISE, TRUST_NOISE]

    candidates = build_upcoming_universe(client)

    assert len(candidates) == 1
    assert candidates[0]["ticker"] == "ACRB"
