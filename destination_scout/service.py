"""Destination Scout service orchestrating SearchAPI + Open-Meteo calls."""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from datetime import date, timedelta
from typing import Any

import httpx
from pydantic import BaseModel, Field, PositiveInt, conint, model_validator

logger = logging.getLogger(__name__)

ALLOWED_INTERESTS: tuple[str, ...] = ("popular", "outdoors", "beaches", "museums", "history", "skiing")


class DestinationScoutError(RuntimeError):
    """Raised when downstream services fail."""


class TimeWindow(BaseModel):
    """Normalized time window coming from the supervisor."""

    token: str = Field(..., min_length=3)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_range(self) -> TimeWindow:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")
        return self


class DestinationScoutRequest(BaseModel):
    """Input contract for the Destination Scout Lambda."""

    departure_id: str = Field(..., min_length=3)
    time_window: TimeWindow
    adults: PositiveInt = 1
    interests: list[str] = Field(default_factory=list)
    arrival_ids: list[str] = Field(default_factory=list)
    limit: PositiveInt = 24
    max_cards: PositiveInt = 3
    include_weather: bool = True
    forecast_days: int = Field(7, ge=1, le=16)

    @model_validator(mode="after")
    def clamp_max_cards(self) -> DestinationScoutRequest:
        if self.max_cards > self.limit:
            self.max_cards = self.limit
        return self


class WeatherSummary(BaseModel):
    """Condensed Open-Meteo snapshot."""

    headline: str
    temperature_high_c: float | None = None
    temperature_low_c: float | None = None
    precipitation_chance: int | None = None
    wind_speed_max_kmh: float | None = None


class DestinationCard(BaseModel):
    """Structured destination output returned to the Supervisor."""

    destination: str
    arrival_id: str | None = None
    country: str | None = None
    why_now: str
    events: list[str] = Field(default_factory=list)
    weather: WeatherSummary | None = None
    sources: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DestinationScoutResponse(BaseModel):
    """Top-level payload returned by the Lambda."""

    cards: list[DestinationCard]
    remaining_candidates: int = 0
    search_metadata: dict[str, Any] = Field(default_factory=dict)


class SearchAPIClient:
    """Thin HTTP client for SearchAPI google_travel_explore calls."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._timeout = timeout
        self._transport = transport

    def explore(self, request: DestinationScoutRequest) -> dict[str, Any]:
        params: dict[str, Any] = {
            "engine": "google_travel_explore",
            "departure_id": request.departure_id,
            "time_period": _build_time_period(request.time_window),
            "travel_mode": "flights_only",
            "adults": request.adults,
            "limit": request.limit,
            "gl": "DE",
            "hl": "en-GB",
            "currency": "EUR",
            "alliance": "STAR_ALLIANCE",
        }
        if request.arrival_ids:
            params["arrival_id"] = request.arrival_ids[0]
        if request.interests:
            filtered = _filter_interests(request.interests)
            if filtered:
                params["interests"] = ",".join(filtered)

        headers = {"Authorization": f"Bearer {self._api_key}"}
        params["api_key"] = self._api_key
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.get(self._base_url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise DestinationScoutError(
                f"SearchAPI explore failed with status {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise DestinationScoutError("SearchAPI explore failed") from exc


class OpenMeteoClient:
    """Thin HTTP client for Open-Meteo daily forecasts."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._transport = transport

    def fetch_daily(
        self,
        latitude: float,
        longitude: float,
        *,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": ",".join(
                [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_probability_max",
                    "wind_speed_10m_max",
                ]
            ),
            "timezone": "UTC",
            "windspeed_unit": "kmh",
        }
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.get(self._base_url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise DestinationScoutError(
                f"Open-Meteo forecast failed with status {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise DestinationScoutError("Open-Meteo forecast failed") from exc


class DestinationScoutService:
    """Coordinates SearchAPI and Open-Meteo to produce destination cards."""

    def __init__(
        self,
        search_client: SearchAPIClient,
        weather_client: OpenMeteoClient,
        *,
        pacing_delay: float = 0.5,
        cache_size: int = 16,
    ) -> None:
        self._search_client = search_client
        self._weather_client = weather_client
        self._pacing_delay = pacing_delay
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._cache_size = max(1, cache_size)

    def generate_cards(self, request: DestinationScoutRequest) -> DestinationScoutResponse:
        cache_key = self._cache_key(request)
        payload = self._cache.get(cache_key)
        if payload is None:
            payload = self._search_client.explore(request)
            self._remember(cache_key, payload)
            if self._pacing_delay:
                time.sleep(self._pacing_delay)
        else:
            logger.debug("Destination Scout cache hit for %s", cache_key)

        candidates = self._extract_candidates(payload)
        cards: list[DestinationCard] = []

        for candidate in candidates:
            if len(cards) >= request.max_cards:
                break
            card = self._candidate_to_card(candidate, request, payload)
            if card:
                cards.append(card)

        metadata = {
            "time_period_token": request.time_window.token,
            "result_count": len(candidates),
            "search_url": payload.get("search_metadata", {}).get("google_url"),
        }
        remaining = max(len(candidates) - len(cards), 0)
        return DestinationScoutResponse(
            cards=cards,
            remaining_candidates=remaining,
            search_metadata=metadata,
        )

    def _extract_candidates(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        candidate_keys = (
            "explore_results",
            "destinations",
            "organic_results",
            "results",
        )
        for key in candidate_keys:
            bucket = payload.get(key)
            if isinstance(bucket, list):
                return [item for item in bucket if isinstance(item, dict)]
        travel_results = payload.get("travel_results")
        if isinstance(travel_results, dict):
            bucket = travel_results.get("destinations")
            if isinstance(bucket, list):
                return [item for item in bucket if isinstance(item, dict)]
        return []

    def _candidate_to_card(
        self,
        candidate: dict[str, Any],
        request: DestinationScoutRequest,
        payload: dict[str, Any],
    ) -> DestinationCard | None:
        destination = (
            candidate.get("destination")
            or candidate.get("title")
            or candidate.get("name")
            or candidate.get("city")
        )
        if not destination:
            logger.debug("Skipping candidate without destination name: %s", candidate)
            return None

        arrival_id = (
            candidate.get("iata_code")
            or candidate.get("iata")
            or candidate.get("arrival_id")
            or candidate.get("airport_code")
        )
        country = candidate.get("country") or candidate.get("region")
        why_now = (
            candidate.get("snippet")
            or candidate.get("description")
            or candidate.get("tagline")
            or candidate.get("why_visit")
            or "Trending inspiration within the Lufthansa Group network."
        )
        events = _normalise_events(candidate.get("top_sights") or candidate.get("events") or [])
        coords = candidate.get("coordinates") or candidate.get("geo") or {}
        latitude = _coerce_float(coords.get("latitude"))
        longitude = _coerce_float(coords.get("longitude"))

        weather: WeatherSummary | None = None
        if request.include_weather and latitude is not None and longitude is not None:
            weather = self._build_weather_summary(latitude, longitude, request)

        sources = [
            candidate.get("link"),
            payload.get("search_metadata", {}).get("google_url"),
        ]
        if weather:
            sources.append("open-meteo")

        metadata = {
            "price_text": candidate.get("price") or candidate.get("price_text"),
            "travel_token": request.time_window.token,
        }

        return DestinationCard(
            destination=destination,
            arrival_id=arrival_id,
            country=country,
            why_now=why_now.strip(),
            events=events,
            weather=weather,
            sources=[src for src in sources if src],
            metadata=metadata,
        )

    def _build_weather_summary(
        self,
        latitude: float,
        longitude: float,
        request: DestinationScoutRequest,
    ) -> WeatherSummary | None:
        start_date, end_date = self._derive_weather_window(request)
        if start_date - date.today() > timedelta(days=16):
            logger.debug("Skipping weather lookup beyond Open-Meteo forecast horizon")
            return None
        try:
            forecast = self._weather_client.fetch_daily(
                latitude,
                longitude,
                start_date=start_date,
                end_date=end_date,
            )
        except DestinationScoutError as exc:
            logger.warning("Open-Meteo lookup failed for %s,%s: %s", latitude, longitude, exc)
            return None
        return _format_weather(forecast)

    def _derive_weather_window(self, request: DestinationScoutRequest) -> tuple[date, date]:
        start_date = request.time_window.start_date or date.today()
        if request.time_window.end_date:
            end_date = request.time_window.end_date
        else:
            end_date = start_date + timedelta(days=request.forecast_days - 1)
        return start_date, end_date

    def _cache_key(self, request: DestinationScoutRequest) -> str:
        arrival_id = request.arrival_ids[0].upper() if request.arrival_ids else "-"
        interest_key = ",".join(sorted(request.interests)) or "-"
        return "|".join(
            [
                request.departure_id.upper(),
                arrival_id,
                request.time_window.token,
                interest_key,
            ]
        )

    def _remember(self, key: str, payload: dict[str, Any]) -> None:
        self._cache[key] = payload
        self._cache.move_to_end(key)
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)


def _build_time_period(time_window: TimeWindow, *, today: date | None = None) -> str:
    today = today or date.today()
    start = time_window.start_date
    end = time_window.end_date
    if start and end:
        return f"{start.isoformat()}..{end.isoformat()}"
    if start:
        return start.isoformat()
    token = (time_window.token or "").strip()
    normalized = _normalize_time_period_token(token, today=today)
    return normalized or "one_week_trip_in_the_next_six_months"


def _normalize_time_period_token(token: str, *, today: date) -> str | None:
    lowered = token.lower()
    static_tokens = {
        "one_week_trip_in_the_next_six_months",
        "two_week_trip_in_the_next_six_months",
        "weekend_trip_in_the_next_six_months",
        "trip_in_the_next_six_months",
    }
    if lowered in static_tokens:
        return lowered

    for prefix in (
        "one_week_trip_in_",
        "two_week_trip_in_",
        "weekend_in_",
        "trip_in_",
    ):
        if lowered.startswith(prefix):
            month_candidate = lowered[len(prefix) :]
            if month_candidate in _allowed_month_tokens(today):
                return lowered
            return None
    return None


def _allowed_month_tokens(today: date) -> set[str]:
    tokens: set[str] = set()
    year = today.year
    month = today.month
    for _ in range(6):
        month_name = date(year, month, 1).strftime("%B").lower()
        tokens.add(month_name)
        month += 1
        if month > 12:
            month = 1
            year += 1
    return tokens


def _filter_interests(raw: list[str]) -> list[str]:
    filtered: list[str] = []
    for interest in raw:
        normalized = (interest or "").strip().lower()
        if normalized in ALLOWED_INTERESTS and normalized not in filtered:
            filtered.append(normalized)
    return filtered


def _normalise_events(raw_events: Any) -> list[str]:
    if isinstance(raw_events, str):
        return [raw_events]
    if isinstance(raw_events, list):
        cleaned: list[str] = []
        for item in raw_events:
            if isinstance(item, str):
                cleaned.append(item)
            elif isinstance(item, dict):
                text = item.get("title") or item.get("name")
                if text:
                    cleaned.append(str(text))
        return cleaned
    return []


def _coerce_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_numeric(values: Any) -> float | None:
    if isinstance(values, list) and values:
        return _coerce_float(values[0])
    return None


def _first_int(values: Any) -> int | None:
    if isinstance(values, list) and values:
        try:
            return int(round(float(values[0])))
        except (TypeError, ValueError):
            return None
    return None


def _format_weather(payload: dict[str, Any]) -> WeatherSummary | None:
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        return None

    high = _first_numeric(daily.get("temperature_2m_max"))
    low = _first_numeric(daily.get("temperature_2m_min"))
    precip = _first_int(daily.get("precipitation_probability_max"))
    wind = _first_numeric(daily.get("wind_speed_10m_max") or daily.get("windspeed_10m_max"))

    if high is None and low is None and precip is None and wind is None:
        return None

    temperature_phrase = None
    if high is not None and low is not None:
        temperature_phrase = f"{round(high):.0f}°C high / {round(low):.0f}°C low"
    elif high is not None:
        temperature_phrase = f"{round(high):.0f}°C daytime high"
    elif low is not None:
        temperature_phrase = f"{round(low):.0f}°C overnight low"

    precip_phrase = f"precip {precip}% chance" if precip is not None else None
    wind_phrase = f"wind gusts {round(wind):.0f} km/h" if wind is not None else None

    headline_parts = [part for part in (temperature_phrase, precip_phrase, wind_phrase) if part]
    headline = "; ".join(headline_parts) if headline_parts else "Weather snapshot unavailable"

    return WeatherSummary(
        headline=headline,
        temperature_high_c=high,
        temperature_low_c=low,
        precipitation_chance=precip,
        wind_speed_max_kmh=wind,
    )


__all__ = [
    "DestinationCard",
    "DestinationScoutError",
    "DestinationScoutRequest",
    "DestinationScoutResponse",
    "DestinationScoutService",
    "OpenMeteoClient",
    "SearchAPIClient",
    "TimeWindow",
    "WeatherSummary",
]
