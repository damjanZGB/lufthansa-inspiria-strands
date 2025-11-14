"""Supervisor agent factory."""

from __future__ import annotations

from strands import Agent
from strands.models import BedrockModel
from strands.tools import PythonAgentTool
from strands_tools import current_time, http_request

from config.settings import get_settings
from shared.prompts import SUPERVISOR_PROMPT_TEMPLATE
from supervisor.tools import call_destination_scout, call_flight_search, call_weather_snapshot

HTTP_REQUEST_TOOL = PythonAgentTool(
    "http_request",
    http_request.TOOL_SPEC,
    http_request.http_request,
)


def build_agent() -> Agent:
    """Instantiate the Strands supervisor agent."""

    settings = get_settings()
    prompt = SUPERVISOR_PROMPT_TEMPLATE.format(
        searchapi_endpoint=settings.searchapi_endpoint,
        searchapi_key=settings.searchapi_key,
    )
    model = BedrockModel(
        model_id=settings.bedrock_model_id,
        region_name=settings.bedrock_region,
        temperature=settings.bedrock_temperature,
        max_tokens=settings.bedrock_max_tokens,
    )
    tools = [
        HTTP_REQUEST_TOOL,
        CURRENT_TIME_TOOL,
        call_flight_search,
        call_destination_scout,
        call_weather_snapshot,
    ]
    return Agent(model=model, system_prompt=prompt, tools=tools)
CURRENT_TIME_TOOL = current_time.current_time
