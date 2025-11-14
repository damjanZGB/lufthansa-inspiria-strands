from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from flight_search.service import (
    CalendarWindow,
    FlightSearchRequest,
    FlightSearchService,
    SearchAPIClient,
)


def _transport(payload: dict[str, Any], status: int = 200) -> httpx.BaseTransport:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)

    return httpx.MockTransport(handler)


def test_flight_service_returns_calendar_when_requested() -> None:
    flights_payload = {
        "search_metadata": {"google_url": "https://www.google.com/travel/flights"},
        "best_flights": [{"itinerary": "LH123", "price": "€431"}],
    }
    calendar_payload = {
        "search_metadata": {"google_url": "https://www.google.com/travel/flights/calendar"},
        "price_matrix": [],
    }
    flights_client = SearchAPIClient(
        base_url="https://example.com/search",
        api_key="token",
        transport=_transport(flights_payload),
    )
    calendar_client = SearchAPIClient(
        base_url="https://example.com/search",
        api_key="token",
        transport=_transport(calendar_payload),
    )
    service = FlightSearchService(flights_client, calendar_client)

    request = FlightSearchRequest(
        departure_id="FRA",
        arrival_id="JFK",
        outbound_date=date(2026, 3, 1),
        calendar_window=CalendarWindow(
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        ),
    )

    response = service.search(request)

    assert response.flights["best_flights"][0]["itinerary"] == "LH123"
    assert response.calendar["price_matrix"] == []
    assert "google_url" in response.metadata
    assert response.metadata["price_hint"]["currency"] == "EUR"


def test_flight_service_handles_calendar_failure_gracefully() -> None:
    flights_payload = {"best_flights": []}
    flights_client = SearchAPIClient(
        base_url="https://example.com/search",
        api_key="token",
        transport=_transport(flights_payload),
    )

    def failing_calendar(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    calendar_client = SearchAPIClient(
        base_url="https://example.com/search",
        api_key="token",
        transport=httpx.MockTransport(failing_calendar),
    )
    service = FlightSearchService(flights_client, calendar_client)

    request = FlightSearchRequest(
        departure_id="MUC",
        arrival_id="EWR",
        outbound_date=date(2026, 5, 10),
        calendar_window=CalendarWindow(
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 31),
        ),
    )

    response = service.search(request)

    assert response.calendar is None


def test_flight_service_expands_to_star_alliance_when_empty() -> None:
    counter = {"calls": 0}

    def flight_handler(_request: httpx.Request) -> httpx.Response:
        if counter["calls"] == 0:
            counter["calls"] += 1
            return httpx.Response(200, json={"best_flights": [], "other_flights": []})
        return httpx.Response(
            200,
            json={
                "best_flights": [{"itinerary": "LX400", "price": "€310"}],
                "search_metadata": {"google_url": "https://www.google.com/flights"},
            },
        )

    flights_client = SearchAPIClient(
        base_url="https://example.com/search",
        api_key="token",
        transport=httpx.MockTransport(flight_handler),
    )
    service = FlightSearchService(flights_client)

    request = FlightSearchRequest(
        departure_id="ZRH",
        arrival_id="EWR",
        outbound_date=date(2026, 7, 2),
    )

    response = service.search(request)

    assert response.flights["best_flights"][0]["itinerary"] == "LX400"
    assert response.metadata["search_scope"] == "star_alliance"
