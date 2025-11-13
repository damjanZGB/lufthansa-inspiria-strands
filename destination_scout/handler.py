"""AWS Lambda-style handler for the Destination Scout service."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from config.settings import get_settings
from destination_scout.service import (
    DestinationScoutRequest,
    DestinationScoutService,
    OpenMeteoClient,
    SearchAPIClient,
)

logger = logging.getLogger(__name__)

settings = get_settings()

_search_client = SearchAPIClient(
    base_url=str(settings.searchapi_endpoint),
    api_key=settings.searchapi_key,
)
_weather_client = OpenMeteoClient(base_url=str(settings.open_meteo_endpoint))
_service = DestinationScoutService(_search_client, _weather_client)


def lambda_handler(event: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    """Entry point compatible with AWS Lambda."""

    try:
        request = DestinationScoutRequest.model_validate(event)
    except ValidationError as exc:
        logger.error("Invalid Destination Scout payload: %s", exc)
        raise

    response = _service.generate_cards(request)
    return response.model_dump()
