from __future__ import annotations

from destination_scout.service import DestinationScoutResponse, DestinationCard
from flight_search.service import FlightSearchResponse
from supervisor import tools as supervisor_tools


class DummyFlightService:
    def __init__(self) -> None:
        self.last_request = None

    def search(self, request):
        self.last_request = request
        return FlightSearchResponse(flights={"best_flights": []}, calendar=None, metadata={})


class DummyDestinationService:
    def __init__(self) -> None:
        self.last_request = None

    def generate_cards(self, request):
        self.last_request = request
        card = DestinationCard(
            destination="Lisbon",
            why_now="Atlantic breezes.",
            metadata={},
        )
        return DestinationScoutResponse(cards=[card], remaining_candidates=0)


def test_call_flight_search_returns_success(monkeypatch) -> None:
    dummy_service = DummyFlightService()
    monkeypatch.setattr(supervisor_tools, "_flight_service", dummy_service)

    payload = {
        "departure_id": "FRA",
        "arrival_id": "JFK",
        "outbound_date": "2026-03-01",
    }
    result = supervisor_tools.call_flight_search(payload)

    assert result["status"] == "success"
    assert dummy_service.last_request.departure_id == "FRA"


def test_call_destination_scout_returns_cards(monkeypatch) -> None:
    dummy_service = DummyDestinationService()
    monkeypatch.setattr(supervisor_tools, "_destination_service", dummy_service)

    payload = {
        "departure_id": "FRA",
        "time_window": {"token": "one_week_trip_in_march"},
    }
    result = supervisor_tools.call_destination_scout(payload)

    assert result["status"] == "success"
    assert dummy_service.last_request.time_window.token == "one_week_trip_in_march"


def test_call_flight_search_handles_validation_error(monkeypatch) -> None:
    monkeypatch.setattr(supervisor_tools, "_flight_service", DummyFlightService())

    result = supervisor_tools.call_flight_search({"departure_id": "FRA"})

    assert result["status"] == "error"


def test_call_weather_snapshot_returns_summary(monkeypatch) -> None:
    def fake_fetch(**_: object) -> dict[str, object]:
        return {"daily": {"temperature_2m_max": [20], "temperature_2m_min": [10]}}

    monkeypatch.setattr(supervisor_tools, "fetch_weather_snapshot", fake_fetch)
    result = supervisor_tools.call_weather_snapshot(
        {
            "latitude": 48.1,
            "longitude": 11.6,
            "start_date": "2025-11-15",
            "end_date": "2025-11-18",
        }
    )

    assert result["status"] == "success"
    assert "summary" in result["data"]


def test_call_flight_search_rejects_past_dates(monkeypatch) -> None:
    dummy_service = DummyFlightService()
    monkeypatch.setattr(supervisor_tools, "_flight_service", dummy_service)

    payload = {
        "departure_id": "FRA",
        "arrival_id": "JFK",
        "outbound_date": "2023-01-01",
    }

    result = supervisor_tools.call_flight_search(payload)
    assert result["status"] == "error"
    assert "current_time" in result["message"]
