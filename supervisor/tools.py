"""Tools that let the supervisor delegate to specialist services."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, ValidationError
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
from supervisor.weather import fetch_weather_snapshot, summarise_weather

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


class WeatherRequest(BaseModel):
    latitude: float
    longitude: float
    start_date: date
    end_date: date


@tool
def call_weather_snapshot(request: dict[str, Any]) -> dict[str, Any]:
    """
    Fetch a weather snapshot for the supplied coordinates and trip window using Open-Meteo.

    Args:
        request: {latitude, longitude, start_date, end_date}.
    Returns:
        {status, data: {summary, raw}} where summary is a concise weather string.
    """

    try:
        parsed = WeatherRequest.model_validate(request)
    except ValidationError as exc:
        return _error(f"Invalid WeatherRequest payload: {exc}")

    horizon = date.today() + timedelta(days=16)
    if parsed.start_date > horizon or parsed.end_date > horizon:
        return _error("Open-Meteo only provides forecasts up to ~16 days ahead.")

    try:
        payload = fetch_weather_snapshot(
            latitude=parsed.latitude,
            longitude=parsed.longitude,
            start_date=parsed.start_date,
            end_date=parsed.end_date,
        )
    except Exception as exc:  # pragma: no cover - network errors
        return _error(f"Open-Meteo lookup failed: {exc}")

    summary = summarise_weather(payload) or "Weather snapshot unavailable"
    return {"status": "success", "data": {"summary": summary, "payload": payload}}


__all__ = ["call_destination_scout", "call_flight_search", "call_weather_snapshot"]
