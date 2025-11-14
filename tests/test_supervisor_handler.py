from __future__ import annotations

import pytest
from pydantic import ValidationError

from supervisor.handler import lambda_handler


def _sample_event() -> dict[str, object]:
    return {
        "persona": "Paula",
        "intent": "Lisbon in March",
        "conversation_state": {
            "destination_cards": [
                {
                    "destination": "Lisbon",
                    "why_now": "Atlantic breezes and tiled hillsides.",
                    "weather": {"headline": "22°C high / 16°C low"},
                }
            ],
            "flight_results": {
                "flights": {
                    "best_flights": [
                        {
                            "itinerary": "LH1172",
                            "price": "€320",
                            "total_duration": "03h 10m",
                            "stops": 0,
                        }
                    ]
                }
            },
        },
    }


def test_lambda_handler_returns_structured_reply() -> None:
    response = lambda_handler(_sample_event(), None)

    assert response["persona"] == "Paula"
    assert "Lisbon" in response["reply"]
    assert response["intent"] == "Lisbon in March"


def test_lambda_handler_rejects_missing_persona() -> None:
    event = _sample_event()
    event.pop("persona")

    with pytest.raises(ValidationError):
        lambda_handler(event, None)
