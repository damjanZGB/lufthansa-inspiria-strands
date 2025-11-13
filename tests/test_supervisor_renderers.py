from __future__ import annotations

from supervisor.composer import compose_reply
from supervisor.renderers import format_destination_cards, format_flight_summary


def test_format_destination_cards_includes_weather_and_sources() -> None:
    cards = [
        {
            "destination": "Lisbon",
            "why_now": "Atlantic breezes and tile-wrapped hills.",
            "weather": {"headline": "24°C high / 16°C low; precip 10%"},
            "events": ["Azulejo Festival"],
            "sources": ["https://example.com/explore/lisbon"],
        }
    ]
    rendered = format_destination_cards(cards)
    assert "Lisbon" in rendered
    assert "Weather" in rendered
    assert "Sources" in rendered


def test_format_flight_summary_highlights_price_hint() -> None:
    flights_payload = {
        "best_flights": [
            {
                "itinerary": "LH401",
                "price": "€640",
                "total_duration": "09h 15m",
                "stops": 0,
            }
        ]
    }
    metadata = {"price_hint": {"amount": 640, "currency": "EUR"}, "google_url": "https://google"}
    rendered = format_flight_summary(flights_payload, metadata)
    assert "Price hint" in rendered
    assert "LH401" in rendered
    assert "https://google" in rendered


def test_compose_reply_merges_cards_and_flights() -> None:
    conversation_state = {
        "destination_cards": [
            {
                "destination": "Lisbon",
                "why_now": "Atlantic breezes and tile-wrapped hills.",
                "weather": {"headline": "24°C high / 16°C low; precip 10%"},
            }
        ],
        "flight_results": {
            "flights": {
                "best_flights": [
                    {
                        "itinerary": "LH401",
                        "price": "€640",
                        "total_duration": "09h 15m",
                        "stops": 0,
                    }
                ]
            },
            "metadata": {"price_hint": {"amount": 640, "currency": "EUR"}},
        },
    }

    text = compose_reply("Paula", conversation_state, intent="Lisbon in March")

    assert "Lisbon" in text
    assert "Price hint" in text
