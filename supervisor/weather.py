"""Helper utilities for fetching destination weather snapshots."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable

import httpx

from config.settings import get_settings


def fetch_weather_snapshot(
    *,
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """Call Open-Meteo daily forecast."""

    settings = get_settings()
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
        "timezone": settings.default_timezone,
    }
    with httpx.Client(timeout=15) as client:
        response = client.get(str(settings.open_meteo_endpoint), params=params)
        response.raise_for_status()
        return response.json()


def summarise_weather(payload: dict[str, Any]) -> str | None:
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        return None

    def _first(values: Iterable[Any]) -> Any | None:
        try:
            return next(iter(values))
        except StopIteration:
            return None

    max_temp = _first(daily.get("temperature_2m_max") or [])
    min_temp = _first(daily.get("temperature_2m_min") or [])
    precip = _first(daily.get("precipitation_probability_max") or [])
    wind = _first(daily.get("wind_speed_10m_max") or [])

    parts = []
    if max_temp is not None and min_temp is not None:
        parts.append(f"{round(max_temp)}°C high / {round(min_temp)}°C low")
    elif max_temp is not None:
        parts.append(f"{round(max_temp)}°C daytime high")
    elif min_temp is not None:
        parts.append(f"{round(min_temp)}°C overnight low")
    if precip is not None:
        parts.append(f"precip {round(precip)}% chance")
    if wind is not None:
        parts.append(f"wind gusts {round(wind)} km/h")

    return "; ".join(parts) if parts else None


__all__ = ["fetch_weather_snapshot", "summarise_weather"]
