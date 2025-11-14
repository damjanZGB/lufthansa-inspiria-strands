#!/usr/bin/env python3
"""Invoke the Supervisor composer handler locally."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from supervisor.handler import lambda_handler

SAMPLE_PAYLOAD: dict[str, Any] = {
    "persona": "Paula",
    "intent": "Lisbon in March",
    "conversation_state": {
        "destination_cards": [
            {
                "destination": "Lisbon",
                "why_now": "Atlantic breezes, open-air tiles, and pastel sunsets.",
                "weather": {"headline": "22°C high / 14°C low; precip 15%"},
                "events": ["Azulejo Festival"],
                "sources": ["https://www.google.com/travel/explore"],
            }
        ],
        "flight_results": {
            "flights": {
                "best_flights": [
                    {
                        "itinerary": "LH1172 FRA → LIS",
                        "price": "€320",
                        "total_duration": "03h 10m",
                        "stops": 0,
                    }
                ]
            },
            "metadata": {
                "price_hint": {"amount": 320, "currency": "EUR"},
                "google_url": "https://www.google.com/travel/flights",
            },
        },
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Supervisor composer Lambda locally with a JSON payload.",
    )
    parser.add_argument(
        "payload",
        nargs="?",
        help="Path to a JSON file containing the ComposeRequest payload.",
    )
    return parser.parse_args()


def load_payload(path: str | None) -> dict[str, Any]:
    if not path:
        return SAMPLE_PAYLOAD

    payload_path = Path(path)
    with payload_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    args = parse_args()
    payload = load_payload(args.payload)
    response = lambda_handler(payload, None)
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
