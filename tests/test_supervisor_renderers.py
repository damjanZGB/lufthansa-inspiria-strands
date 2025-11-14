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
                "segments": [
                    {
                        "airline_code": "LH",
                        "flight_number": "401",
                        "departure_airport": "FRA",
                        "arrival_airport": "JFK",
                        "departure_time": "2026-03-01T09:10:00",
                        "arrival_time": "2026-03-01T12:05:00",
                        "aircraft": "Airbus A350",
                        "amenities": ["Wi-Fi"],
                        "seat_type": "Below Average Legroom (29 inches)",
                    }
                ],
                "baggage": "Bag and fare conditions depend on the return flight",
            }
        ]
    }
    metadata = {"price_hint": {"amount": 640, "currency": "EUR"}, "google_url": "https://google"}
    rendered = format_flight_summary(flights_payload, metadata)
    assert "Price hint" in rendered
    assert "Direct Flights" in rendered
    assert "**Aircraft**: Airbus A350" in rendered
    assert "**Baggage**" in rendered
    assert "https://google" in rendered


def test_compose_reply_merges_cards_and_flights() -> None:
    conversation_state = {
        "destination_cards": [
            {
                "destination": "Lisbon",
                "why_now": "Atlantic breezes and tile-wrapped hills.",
                "weather": {"headline": "24°C high / 16°C low; precip 10%"},
                "arrival_id": "LIS",
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
                        "segments": [
                            {
                                "airline_code": "LH",
                                "flight_number": "401",
                                "departure_airport": "FRA",
                                "arrival_airport": "LIS",
                                "departure_time": "2026-03-01T09:10:00",
                                "arrival_time": "2026-03-01T11:10:00",
                                "aircraft": "Airbus A350",
                                "amenities": ["Wi-Fi"],
                                "seat_type": "Below Average Legroom (29 inches)",
                                "has_usb": True,
                            },
                            {
                                "airline_code": "LH",
                                "flight_number": "402",
                                "departure_airport": "LIS",
                                "arrival_airport": "FRA",
                                "departure_time": "2026-03-10T14:00:00",
                                "arrival_time": "2026-03-10T18:30:00",
                            },
                        ],
                        "baggage": "Bag and fare conditions depend on the return flight",
                    }
                ]
            },
            "metadata": {"price_hint": {"amount": 640, "currency": "EUR"}},
        },
    }

    text = compose_reply("Paula", conversation_state, intent="Lisbon in March")

    assert "Lisbon" in text
    assert "Price hint" in text
    assert "Destination Weather" in text


def test_gina_questionnaire_appended_when_missing_choice() -> None:
    text = compose_reply("Gina", {})
    assert "travel personality best fits you" in text


def test_gina_questionnaire_omitted_when_choice_present() -> None:
    conversation_state = {"travel_personality_choice": "2"}
    text = compose_reply("Gina", conversation_state)
    assert "travel personality best fits you" not in text
