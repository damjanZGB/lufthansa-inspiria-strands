"""Supervisor composer that turns conversation state into persona responses."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from supervisor.renderers import (
    build_destination_weather_report,
    format_destination_cards,
    format_flight_summary,
)

PERSONA_OPENERS = {
    "paula": "Hi, I am Paula. Here's what I gathered for you:",
    "gina": "Gina here — tailored insights coming your way:",
    "bianca": "Bianca speaking with a spark of inspiration:",
}

PERSONA_CLOSERS = {
    "paula": "Let me know if you'd like to adjust any detail.",
    "gina": "Would you like to refine these choices further?",
    "bianca": "Shall we explore another vibe or lock this in?",
}

GINA_PERSONALITY_QUESTION = (
    "Before we go further, which travel personality best fits you? Choose 1–4:\n"
    "1) The Analytical Curator – value rationality in deciding and control in planning\n"
    "2) The Rational Explorer – value rationality in deciding and freedom in planning\n"
    "3) The Sentimental Voyager – value feelings in deciding and control in planning\n"
    "4) The Experiential Libertine – value feelings in deciding and freedom in planning"
)


def compose_reply(
    persona: str,
    conversation_state: Mapping[str, Any],
    *,
    intent: str | None = None,
) -> str:
    """Build a final response string given persona + conversation state."""

    persona_key = persona.lower()
    opener = PERSONA_OPENERS.get(persona_key, "Hello from the Lufthansa Inspiria supervisor:")
    sections = [opener]

    if persona_key == "gina" and not conversation_state.get("travel_personality_choice"):
        # Gina must always surface the persona questionnaire immediately after the opener.
        sections.append(GINA_PERSONALITY_QUESTION)

    if intent:
        sections.append(f"Traveler intent: {intent}")

    destination_cards = conversation_state.get("destination_cards")
    if isinstance(destination_cards, list) and destination_cards:
        sections.append(format_destination_cards(destination_cards))

    flight_results = conversation_state.get("flight_results")
    if isinstance(flight_results, Mapping):
        flights_payload = flight_results.get("flights")
        metadata = flight_results.get("metadata") or {}
        if isinstance(flights_payload, Mapping):
            sections.append(format_flight_summary(flights_payload, metadata))
    weather_report = build_destination_weather_report(conversation_state)
    if weather_report:
        sections.append(weather_report)

    closer = PERSONA_CLOSERS.get(persona_key, "Let me know if you'd like to explore more options.")
    sections.append(closer)
    return "\n\n".join(sections)


__all__ = ["compose_reply"]
