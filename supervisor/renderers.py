"""Utility formatters for Supervisor outputs."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from shared.flight_utils import normalise_price


def format_destination_cards(cards: Iterable[dict[str, Any]]) -> str:
    """Return a bullet-style summary of destination scout cards."""

    lines: list[str] = []
    lines.append("### Inspiration Cards")
    for idx, card in enumerate(cards, 1):
        destination = card.get("destination") or card.get("arrival_id") or "Unknown"
        why_now = card.get("why_now") or "No highlights provided."
        weather = (card.get("weather") or {}).get("headline")
        weather_line = f"Weather: {weather}" if weather else "Weather: (pending lookup)"
        events = card.get("events") or []
        events_line = f"Events: {', '.join(events[:3])}" if events else "Events: not listed."
        sources = card.get("sources") or []
        source_line = f"Sources: {', '.join(sources[:2])}" if sources else "Sources: SearchAPI"
        lines.append(f"{idx}. **{destination}** — {why_now}")
        lines.append(f"   {weather_line}")
        lines.append(f"   {events_line}")
        lines.append(f"   {source_line}")
    return "\n".join(lines)


def format_flight_summary(
    flights_payload: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> str:
    """Return a textual summary of SearchAPI flight results."""

    metadata = metadata or {}
    sections: list[str] = []
    best = flights_payload.get("best_flights")
    if isinstance(best, list) and best:
        sections.append(_format_flight_section("Best Flights", best))
    others = flights_payload.get("other_flights")
    if isinstance(others, list) and others:
        sections.append(_format_flight_section("Alternatives", others))
    if not sections:
        sections.append("No priced itineraries were returned. Request a different date or airport.")

    price_hint = metadata.get("price_hint")
    if isinstance(price_hint, dict):
        price_line = f"Price hint: {price_hint.get('amount')} {price_hint.get('currency')}"
        sections.append(price_line)
    google_url = metadata.get("google_url")
    if google_url:
        sections.append(f"View on Google Flights: {google_url}")
    calendar_url = metadata.get("calendar_url")
    if calendar_url:
        sections.append(f"Calendar grid: {calendar_url}")
    return "\n\n".join(sections)


def _format_flight_section(title: str, flights: list[dict[str, Any]]) -> str:
    lines = [f"### {title}"]
    for idx, flight in enumerate(flights, 1):
        itinerary = flight.get("itinerary") or flight.get("title") or "Unnamed"
        price = flight.get("price") or flight.get("price_per_ticket")
        normalized = normalise_price(price)
        price_text = (
            f"{normalized['amount']:.0f} {normalized['currency']}"
            if normalized
            else (price or "N/A")
        )
        duration = flight.get("total_duration") or flight.get("duration")
        stops = flight.get("stops") or flight.get("number_of_stops")
        stops_text = f"{stops} stops" if stops else "stops data unavailable"
        lines.append(
            f"{idx}. {itinerary} • {duration or 'duration N/A'} • {stops_text} • {price_text}"
        )
    return "\n".join(lines)


__all__ = ["format_destination_cards", "format_flight_summary"]
