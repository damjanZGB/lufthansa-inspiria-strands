"""Flight search service wrapping SearchAPI google_flights + calendar."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, PositiveInt, conint, model_validator

from shared.flight_utils import LH_GROUP_AIRLINES, airlines_csv, extract_best_price, star_alliance_list

logger = logging.getLogger(__name__)


class FlightSearchError(RuntimeError):
    """Raised when SearchAPI requests fail."""


class CalendarWindow(BaseModel):
    """Calendar pricing window."""

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_window(self) -> CalendarWindow:
        if self.start_date > self.end_date:
            raise ValueError("calendar start_date cannot be after end_date")
        return self


class FlightSearchRequest(BaseModel):
    """Input contract for the flight search Lambda."""

    departure_id: str = Field(..., min_length=3)
    arrival_id: str = Field(..., min_length=3)
    outbound_date: date
    return_date: date | None = None
    adults: PositiveInt = 1
    travel_class: Literal["economy", "premium_economy", "business", "first"] = "economy"
    stops: Literal["any", "nonstop"] = "any"
    included_airlines: list[str] = Field(default_factory=lambda: list(LH_GROUP_AIRLINES))
    currency: str = "EUR"
    locale: str = "en"
    region: str = "DE"
    calendar_window: CalendarWindow | None = None
    calendar_limit: conint(ge=1, le=60) = 30

    @property
    def included_airlines_param(self) -> str:
        return airlines_csv(self.included_airlines)


class FlightSearchResponse(BaseModel):
    """Structured response returned by the service."""

    flights: dict[str, Any]
    calendar: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchAPIClient:
    """Simple HTTP client for google_flights + calendar endpoints."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._timeout = timeout
        self._transport = transport

    def flights(self, request: FlightSearchRequest) -> dict[str, Any]:
        params = {
            "engine": "google_flights",
            "departure_id": request.departure_id,
            "arrival_id": request.arrival_id,
            "outbound_date": request.outbound_date.isoformat(),
            "travel_class": request.travel_class,
            "stops": request.stops,
            "adults": request.adults,
            "hl": request.locale,
            "gl": request.region,
            "currency": request.currency,
            "included_airlines": request.included_airlines_param,
        }
        if request.return_date:
            params["return_date"] = request.return_date.isoformat()

        return self._perform_request(params, "google_flights")

    def calendar(self, request: FlightSearchRequest) -> dict[str, Any]:
        if not request.calendar_window:
            raise ValueError("calendar_window missing")
        params = {
            "engine": "google_flights_calendar",
            "departure_id": request.departure_id,
            "arrival_id": request.arrival_id,
            "start_date": request.calendar_window.start_date.isoformat(),
            "end_date": request.calendar_window.end_date.isoformat(),
            "travel_class": request.travel_class,
            "stops": request.stops,
            "adults": request.adults,
            "hl": request.locale,
            "gl": request.region,
            "currency": request.currency,
            "included_airlines": request.included_airlines_param,
            "limit": request.calendar_limit,
        }
        return self._perform_request(params, "google_flights_calendar")

    def _perform_request(self, params: dict[str, Any], engine: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        params = {**params, "api_key": self._api_key}
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.get(self._base_url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise FlightSearchError(
                f"SearchAPI {engine} failed with status {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - network exceptions
            raise FlightSearchError(f"SearchAPI {engine} failed") from exc


class FlightSearchService:
    """Coordinates SearchAPI flight + calendar calls."""

    def __init__(
        self,
        flights_client: SearchAPIClient,
        calendar_client: SearchAPIClient | None = None,
    ) -> None:
        self._flights_client = flights_client
        self._calendar_client = calendar_client or flights_client

    def search(self, request: FlightSearchRequest) -> FlightSearchResponse:
        flights_payload = self._flights_client.flights(request)
        search_scope = "lh_group"
        if _is_empty_payload(flights_payload):
            fallback_request = request.model_copy(update={"included_airlines": star_alliance_list()})
            flights_payload = self._flights_client.flights(fallback_request)
            search_scope = "star_alliance"
        calendar_payload = None
        if request.calendar_window:
            try:
                calendar_payload = self._calendar_client.calendar(request)
            except FlightSearchError as exc:
                logger.warning("Calendar lookup failed: %s", exc)

        metadata = {
            "google_url": flights_payload.get("search_metadata", {}).get("google_url"),
            "calendar_url": (
                (calendar_payload or {}).get("search_metadata", {}).get("google_url")
                if calendar_payload
                else None
            ),
            "price_hint": extract_best_price(
                flights_payload,
                currency=request.currency,
            ),
            "search_scope": search_scope,
        }
        return FlightSearchResponse(
            flights=flights_payload,
            calendar=calendar_payload,
            metadata={k: v for k, v in metadata.items() if v},
        )


def _is_empty_payload(payload: dict[str, Any]) -> bool:
    for key in ("best_flights", "other_flights"):
        bucket = payload.get(key)
        if isinstance(bucket, list) and bucket:
            return False
    return True


__all__ = [
    "CalendarWindow",
    "FlightSearchError",
    "FlightSearchRequest",
    "FlightSearchResponse",
    "FlightSearchService",
    "SearchAPIClient",
]
