from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from destination_scout.service import (
    DestinationScoutRequest,
    DestinationScoutService,
    OpenMeteoClient,
    SearchAPIClient,
    TimeWindow,
)


def _mock_transport(
    payload: dict[str, Any] | None = None, status: int = 200
) -> httpx.BaseTransport:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload or {})

    return httpx.MockTransport(handler)


def test_generate_cards_includes_weather_snapshot() -> None:
    search_payload = {
        "search_metadata": {"google_url": "https://www.google.com/travel/explore"},
        "explore_results": [
            {
                "destination": "Lisbon",
                "country": "Portugal",
                "snippet": "Mild Atlantic breezes and tiled hillsides.",
                "coordinates": {"latitude": 38.7167, "longitude": -9.139},
                "iata_code": "LIS",
                "link": "https://www.google.com/travel/flights?q=lisbon",
                "price": "from €210",
            }
        ],
    }
    weather_payload = {
        "daily": {
            "time": ["2026-03-01"],
            "temperature_2m_max": [22.1],
            "temperature_2m_min": [12.3],
            "precipitation_probability_max": [25],
            "wind_speed_10m_max": [28.5],
        }
    }
    search_client = SearchAPIClient(
        base_url="https://example.com/search",
        api_key="token",
        transport=_mock_transport(search_payload),
    )
    weather_client = OpenMeteoClient(
        base_url="https://weather.example.com",
        transport=_mock_transport(weather_payload),
    )
    service = DestinationScoutService(
        search_client,
        weather_client,
        pacing_delay=0.0,
    )
    request = DestinationScoutRequest(
        departure_id="FRA",
        time_window=TimeWindow(
            token="one_week_trip_in_march_2026",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 7),
        ),
        interests=["culture"],
        max_cards=1,
    )

    response = service.generate_cards(request)

    assert response.remaining_candidates == 0
    assert len(response.cards) == 1
    card = response.cards[0]
    assert card.destination == "Lisbon"
    assert card.arrival_id == "LIS"
    assert card.weather is not None
    assert "°C" in card.weather.headline
    assert "open-meteo" in card.sources


def test_generate_cards_gracefully_handles_weather_failure() -> None:
    search_payload = {
        "explore_results": [
            {
                "destination": "Reykjavik",
                "country": "Iceland",
                "snippet": "Glaciers, lagoons, and northern lights.",
                "coordinates": {"latitude": 64.1466, "longitude": -21.9426},
                "iata_code": "KEF",
            }
        ]
    }
    search_client = SearchAPIClient(
        base_url="https://example.com/search",
        api_key="token",
        transport=_mock_transport(search_payload),
    )

    def failing_weather_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    weather_client = OpenMeteoClient(
        base_url="https://weather.example.com",
        transport=httpx.MockTransport(failing_weather_handler),
    )
    service = DestinationScoutService(search_client, weather_client, pacing_delay=0.0)
    request = DestinationScoutRequest(
        departure_id="MUC",
        time_window=TimeWindow(token="one_week_trip_in_march_2026"),
        max_cards=1,
    )

    response = service.generate_cards(request)

    assert len(response.cards) == 1
    assert response.cards[0].destination == "Reykjavik"
    assert response.cards[0].weather is None


def test_searchapi_responses_are_cached_between_invocations() -> None:
    call_counter = {"count": 0}

    def search_handler(_request: httpx.Request) -> httpx.Response:
        call_counter["count"] += 1
        return httpx.Response(
            200,
            json={
                "explore_results": [
                    {
                        "destination": "Vienna",
                        "snippet": "Coffee houses and imperial flair.",
                    }
                ]
            },
        )

    search_client = SearchAPIClient(
        base_url="https://example.com/search",
        api_key="token",
        transport=httpx.MockTransport(search_handler),
    )
    weather_client = OpenMeteoClient(
        base_url="https://weather.example.com",
        transport=_mock_transport(),
    )
    service = DestinationScoutService(search_client, weather_client, pacing_delay=0.0)
    request = DestinationScoutRequest(
        departure_id="ZRH",
        time_window=TimeWindow(token="one_week_trip_in_june"),
    )

    service.generate_cards(request)
    service.generate_cards(request)

    assert call_counter["count"] == 1
