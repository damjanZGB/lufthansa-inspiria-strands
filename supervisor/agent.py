"""Supervisor agent factory."""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel
from strands_tools import http_request

from config.settings import get_settings
from shared.prompts import SUPERVISOR_PROMPT_TEMPLATE

HTTP_REQUEST_TOOL = http_request.http_request


def build_agent() -> Agent:
    """Instantiate the Strands supervisor agent."""

    settings = get_settings()
    prompt = SUPERVISOR_PROMPT_TEMPLATE.format(
        searchapi_endpoint=settings.searchapi_endpoint,
        searchapi_key=settings.searchapi_key,
    )
    model = BedrockModel(
        model_id=settings.bedrock_model_id,
        region=settings.bedrock_region,
        temperature=settings.bedrock_temperature,
        max_tokens=settings.bedrock_max_tokens,
    )
    return Agent(model=model, system_prompt=prompt, tools=[HTTP_REQUEST_TOOL])
