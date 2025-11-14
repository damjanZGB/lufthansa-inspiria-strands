"""Utility formatters for Supervisor outputs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from datetime import datetime

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
    flights = _collect_flights(flights_payload)
    direct, connecting = _split_flights(flights)
    if direct:
        sections.append(_render_flight_block("Direct Flights", direct))
    if connecting:
        sections.append(_render_flight_block("Connecting Flights", connecting))
    if not sections:
        sections.append(
            "No priced itineraries were returned. Expanding to Star Alliance and, if still empty, "
            "ask the traveller for permission to include non-Star Alliance carriers."
        )

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


def build_destination_weather_report(conversation_state: Mapping[str, Any]) -> str | None:
    cards = conversation_state.get("destination_cards")
    if not isinstance(cards, list) or not cards:
        return None
    flight_results = conversation_state.get("flight_results") or {}
    flights_payload = flight_results.get("flights")
    if not isinstance(flights_payload, Mapping):
        return None
    flights = _collect_flights(flights_payload)
    if not flights:
        return None
    target_flight = flights[0]
    arrival_code = _extract_arrival_code(target_flight)
    matched_card = _match_destination_card(cards, arrival_code)
    if not matched_card:
        return None
    weather = matched_card.get("weather")
    if not isinstance(weather, Mapping):
        return None
    trip_window = _extract_trip_window(target_flight)
    if not trip_window:
        return None
    destination = matched_card.get("destination") or arrival_code or "Destination"
    headline = weather.get("headline") or "Weather snapshot unavailable"

    return (
        "Destination Weather\n"
        f"{destination} ({trip_window[0]} to {trip_window[1]}): {headline}"
    )


def _collect_flights(payload: dict[str, Any]) -> list[dict[str, Any]]:
    flights: list[dict[str, Any]] = []
    for key in ("best_flights", "other_flights"):
        bucket = payload.get(key)
        if isinstance(bucket, list):
            flights.extend([flight for flight in bucket if isinstance(flight, dict)])
    return flights


def _split_flights(flights: list[dict[str, Any]], max_results: int = 10) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    direct: list[dict[str, Any]] = []
    connecting: list[dict[str, Any]] = []
    for flight in flights:
        target = direct if _is_direct(flight) else connecting
        if len(direct) + len(connecting) >= max_results:
            break
        target.append(flight)
    return direct, connecting


def _render_flight_block(title: str, flights: list[dict[str, Any]]) -> str:
    lines = [title]
    for idx, flight in enumerate(flights, 1):
        lines.append(_format_flight_entry(idx, flight))
    return "\n\n".join(lines)


def _format_flight_entry(index: int, flight: dict[str, Any]) -> str:
    parts: list[str] = []
    segments = flight.get("segments") or []
    if segments:
        parts.append(_format_primary_segment(index, segments[0]))
        for seg in segments[1:]:
            parts.append(_format_connection_segment(seg))
    else:
        itinerary = flight.get("itinerary") or flight.get("title") or "Unnamed itinerary"
        parts.append(f"{index}. **{itinerary}**")

    parts.append(f"**Aircraft**: {_extract_aircraft(segments, flight)}")
    parts.append(f"**Amenities**: {_extract_amenities(segments, flight)}")
    parts.append(f"**Baggage**: {_extract_baggage(flight)}")

    price = flight.get("price") or flight.get("price_per_ticket")
    normalized = normalise_price(price)
    price_text = (
        f"{normalized['amount']:.0f} {normalized['currency']}" if normalized else (price or "N/A")
    )
    stops = flight.get("stops") or flight.get("number_of_stops")
    stops_text = f"{stops} stops" if stops not in (None, "") else "stops data unavailable"
    parts.append(f"**Price: {price_text}. {stops_text}.**")
    return "\n".join(parts)


def _format_primary_segment(index: int, segment: dict[str, Any]) -> str:
    carrier = segment.get("airline_code") or segment.get("carrier") or ""
    flight_number = segment.get("flight_number") or segment.get("number") or ""
    code = f"{carrier}{flight_number}".strip() or "Flight"
    departure = _format_airport(segment.get("departure_airport") or segment.get("departure_id"))
    arrival = _format_airport(segment.get("arrival_airport") or segment.get("arrival_id"))
    dep_time, dep_date = _format_time(segment.get("departure_time"))
    arr_time, arr_date = _format_time(segment.get("arrival_time"))
    next_day = " NEXT DAY" if dep_date and arr_date and dep_date != arr_date else ""
    date_text = dep_date or ""
    return f"{index}. **{code}**: {departure} {dep_time} -> {arrival} {arr_time}{next_day} | {date_text}"


def _format_connection_segment(segment: dict[str, Any]) -> str:
    carrier = segment.get("airline_code") or segment.get("carrier") or ""
    flight_number = segment.get("flight_number") or segment.get("number") or ""
    code = f"{carrier}{flight_number}".strip() or "Flight"
    departure = _format_airport(segment.get("departure_airport") or segment.get("departure_id"))
    arrival = _format_airport(segment.get("arrival_airport") or segment.get("arrival_id"))
    dep_time, dep_date = _format_time(segment.get("departure_time"))
    arr_time, arr_date = _format_time(segment.get("arrival_time"))
    next_day = " NEXT DAY" if dep_date and arr_date and dep_date != arr_date else ""
    date_text = arr_date or ""
    return f"- THEN, **{code}** - {departure} {dep_time} -> {arrival} {arr_time}{next_day} | {date_text}"


def _format_airport(raw: Any) -> str:
    if isinstance(raw, dict):
        return raw.get("code") or raw.get("name") or "Unknown"
    return raw or "Unknown"


def _format_time(raw: Any) -> tuple[str, str | None]:
    if isinstance(raw, str):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return dt.strftime("%H:%M"), dt.date().isoformat()
        except ValueError:
            pass
        return raw, None
    return "?", None


def _extract_aircraft(segments: list[dict[str, Any]], flight: dict[str, Any]) -> str:
    for segment in segments:
        aircraft = segment.get("aircraft") or segment.get("aircraft_type")
        if aircraft:
            return aircraft
    return flight.get("aircraft") or "Not listed"


def _extract_amenities(segments: list[dict[str, Any]], flight: dict[str, Any]) -> str:
    amenities: list[str] = []
    segment_amenities = segments[0].get("amenities") if segments else None
    if isinstance(segment_amenities, list):
        amenities.extend([str(item) for item in segment_amenities if item])
    seat = segments[0].get("seat_type") if segments else None
    if seat:
        amenities.append(f"Seat type {seat}")
    usb = segments[0].get("has_usb") if segments else None
    if usb:
        amenities.append("In-seat USB outlet")
    carbon = flight.get("carbon_emissions") or flight.get("carbon_emission")
    if carbon:
        amenities.append(f"Carbon emission: {carbon}")
    return ", ".join(amenities) if amenities else "Not listed"


def _extract_baggage(flight: dict[str, Any]) -> str:
    for key in ("baggage", "bag_info", "fare_conditions", "fare_details"):
        value = flight.get(key)
        if value:
            return str(value)
    return "Not specified"


def _is_direct(flight: dict[str, Any]) -> bool:
    stops = flight.get("stops") or flight.get("number_of_stops")
    if stops in (0, "0", "nonstop"):
        return True
    segments = flight.get("segments")
    if isinstance(segments, list):
        return len(segments) <= 1
    return False


def _extract_arrival_code(flight: dict[str, Any]) -> str | None:
    segments = flight.get("segments")
    if isinstance(segments, list) and segments:
        arrival = segments[-1].get("arrival_airport") or segments[-1].get("arrival_id")
        if isinstance(arrival, dict):
            return arrival.get("code") or arrival.get("name")
        return arrival
    return flight.get("arrival_id")


def _match_destination_card(cards: list[dict[str, Any]], arrival_code: str | None) -> dict[str, Any] | None:
    if arrival_code:
        for card in cards:
            card_arrival = card.get("arrival_id") or card.get("destination")
            if card_arrival and arrival_code.lower() in str(card_arrival).lower():
                return card
    return cards[0] if cards else None


def _extract_trip_window(flight: dict[str, Any]) -> tuple[str, str] | None:
    segments = flight.get("segments")
    if not isinstance(segments, list) or not segments:
        return None
    depart = _format_time(segments[0].get("departure_time"))[1]
    return_arrival = _format_time(segments[-1].get("arrival_time"))[1]
    if not depart or not return_arrival:
        return None
    return depart, return_arrival


__all__ = ["format_destination_cards", "format_flight_summary"]
