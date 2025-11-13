from __future__ import annotations

from shared.flight_utils import (
    LH_GROUP_AIRLINES,
    airlines_csv,
    extract_best_price,
    lhg_airlines_list,
    normalise_price,
)


def test_lhg_airlines_list_adds_extra_codes() -> None:
    merged = lhg_airlines_list(["ua"])
    assert merged[: len(LH_GROUP_AIRLINES)] == list(LH_GROUP_AIRLINES)
    assert "UA" in merged


def test_airlines_csv_respects_default_order() -> None:
    csv = airlines_csv()
    assert csv.startswith("LH,LX,OS")


def test_normalise_price_parses_strings() -> None:
    price = normalise_price("EUR 512.99")
    assert price == {"amount": 512.99, "currency": "EUR"}


def test_extract_best_price_scans_best_flights() -> None:
    payload = {
        "best_flights": [
            {"price": "€431", "itinerary": "LH401"},
            {"price": "€490"},
        ]
    }
    parsed = extract_best_price(payload, currency="EUR")
    assert parsed == {"amount": 431.0, "currency": "EUR"}
