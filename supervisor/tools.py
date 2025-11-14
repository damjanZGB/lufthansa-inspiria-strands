"""Tools that let the supervisor delegate to specialist services."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from strands import tool

from config.settings import get_settings
from destination_scout.service import (
    DestinationScoutRequest,
    DestinationScoutResponse,
    DestinationScoutService,
    OpenMeteoClient,
    SearchAPIClient as DestinationSearchClient,
)
from flight_search.service import (
    FlightSearchRequest,
    FlightSearchResponse,
    FlightSearchService,
    SearchAPIClient as FlightSearchClient,
)

_flight_service: FlightSearchService | None = None
_destination_service: DestinationScoutService | None = None


def _get_flight_service() -> FlightSearchService:
    global _flight_service
    if _flight_service is None:
        settings = get_settings()
        client = FlightSearchClient(
            base_url=str(settings.searchapi_endpoint),
            api_key=settings.searchapi_key,
        )
        _flight_service = FlightSearchService(client)
    return _flight_service


def _get_destination_service() -> DestinationScoutService:
    global _destination_service
    if _destination_service is None:
        settings = get_settings()
        search_client = DestinationSearchClient(
            base_url=str(settings.searchapi_endpoint),
            api_key=settings.searchapi_key,
        )
        weather_client = OpenMeteoClient(base_url=str(settings.open_meteo_endpoint))
        _destination_service = DestinationScoutService(search_client, weather_client)
    return _destination_service


def _error(message: str) -> dict[str, Any]:
    return {"status": "error", "message": message}


@tool
def call_flight_search(request: dict[str, Any]) -> dict[str, Any]:
    """
    Use the dedicated Flight Search service powered by Google Flights SearchAPI.

    Args:
        request: JSON matching FlightSearchRequest (departure_id, arrival_id, outbound_date, optional return_date,
            adults, travel_class, stops, included_airlines, calendar_window).
    Returns:
        Dict with status=success and SearchAPI payloads (flights, calendar, metadata).
    """

    try:
        parsed = FlightSearchRequest.model_validate(request)
    except ValidationError as exc:
        return _error(f"Invalid FlightSearchRequest: {exc}")

    service = _get_flight_service()
    response: FlightSearchResponse = service.search(parsed)
    return {"status": "success", "data": response.model_dump()}


@tool
def call_destination_scout(request: dict[str, Any]) -> dict[str, Any]:
    """
    Use the Destination Scout service (SearchAPI Explore + Open-Meteo) to fetch cards.

    Args:
        request: JSON matching DestinationScoutRequest (departure_id, time_window token [+ optional dates],
            arrival_ids or interests, max_cards).
    Returns:
        Dict with status=success and cards metadata.
    """

    try:
        parsed = DestinationScoutRequest.model_validate(request)
    except ValidationError as exc:
        return _error(f"Invalid DestinationScoutRequest: {exc}")

    service = _get_destination_service()
    response: DestinationScoutResponse = service.generate_cards(parsed)
    return {"status": "success", "data": response.model_dump()}


__all__ = ["call_destination_scout", "call_flight_search"]
