"""Destination scout agent factory."""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel
from strands.tools import HttpRequestTool

from config.settings import get_settings
from shared.prompts import DESTINATION_SCOUT_PROMPT_TEMPLATE


def build_agent() -> Agent:
    """Return a Strands agent dedicated to destination inspiration."""

    settings = get_settings()
    prompt = DESTINATION_SCOUT_PROMPT_TEMPLATE.format(
        searchapi_endpoint=settings.searchapi_endpoint,
        searchapi_key=settings.searchapi_key,
        open_meteo_endpoint=settings.open_meteo_endpoint,
    )
    model = BedrockModel(
        model_id=settings.bedrock_model_id,
        region=settings.bedrock_region,
        temperature=settings.bedrock_temperature,
        max_tokens=settings.bedrock_max_tokens,
    )
    return Agent(model=model, system_prompt=prompt, tools=[HttpRequestTool()])
