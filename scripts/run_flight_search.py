#!/usr/bin/env python3
"""Invoke the Flight Search service locally."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from flight_search.handler import lambda_handler

EXAMPLE_PAYLOAD: dict[str, Any] = {
    "departure_id": "FRA",
    "arrival_id": "JFK",
    "outbound_date": "2026-03-01",
    "return_date": "2026-03-10",
    "adults": 1,
    "travel_class": "economy",
    "stops": "any",
    "calendar_window": {
        "start_date": "2026-03-01",
        "end_date": "2026-03-31",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Flight Search Lambda locally with a JSON payload."
    )
    parser.add_argument(
        "payload",
        nargs="?",
        help="Path to a JSON file containing the FlightSearchRequest payload.",
    )
    return parser.parse_args()


def load_payload(path: str | None) -> dict[str, Any]:
    if not path:
        return EXAMPLE_PAYLOAD
    payload_path = Path(path)
    with payload_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    if load_dotenv:
        load_dotenv()
    args = parse_args()
    payload = load_payload(args.payload)
    response = lambda_handler(payload, None)
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
