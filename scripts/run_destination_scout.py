#!/usr/bin/env python3
"""Invoke the Destination Scout service locally."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

from destination_scout.handler import lambda_handler

EXAMPLE_PAYLOAD: dict[str, Any] = {
    "departure_id": "FRA",
    "time_window": {
        "token": "one_week_trip_in_march",
        "start_date": "2026-03-01",
        "end_date": "2026-03-07",
    },
    "adults": 2,
    "interests": ["culture"],
    "limit": 24,
    "max_cards": 3,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Destination Scout Lambda locally with a JSON payload."
    )
    parser.add_argument(
        "payload",
        nargs="?",
        help="Path to a JSON file containing the DestinationScoutRequest payload.",
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
        load_dotenv()  # pull SEARCHAPI_KEY from .env when available

    args = parse_args()
    payload = load_payload(args.payload)
    response = lambda_handler(payload, None)
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
