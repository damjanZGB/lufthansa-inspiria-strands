"""AWS Lambda-style handler for the flight search service."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from config.settings import get_settings
from flight_search.service import (
    FlightSearchRequest,
    FlightSearchService,
    SearchAPIClient,
)

logger = logging.getLogger(__name__)

settings = get_settings()
_client = SearchAPIClient(
    base_url=str(settings.searchapi_endpoint),
    api_key=settings.searchapi_key,
)
_service = FlightSearchService(_client)


def lambda_handler(event: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    """Entry point compatible with AWS Lambda."""

    try:
        request = FlightSearchRequest.model_validate(event)
    except ValidationError as exc:
        logger.error("Invalid Flight Search payload: %s", exc)
        raise

    response = _service.search(request)
    return response.model_dump()
