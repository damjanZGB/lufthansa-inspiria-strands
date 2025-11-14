"""AWS Lambda-style handler for composing supervisor replies."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from supervisor.composer import compose_reply

logger = logging.getLogger(__name__)


class ComposeRequest(BaseModel):
    """Payload contract for supervisor composition."""

    persona: str = Field(..., min_length=2, description="Persona identifier, e.g. Paula or Gina.")
    conversation_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Latest Strands conversation_state structure.",
    )
    intent: str | None = Field(
        default=None,
        description="Optional traveler intent string for context.",
    )


class ComposeResponse(BaseModel):
    """Structured response returned by the handler."""

    persona: str
    intent: str | None = None
    reply: str


def render_reply(request: ComposeRequest) -> ComposeResponse:
    """Convert a validated request into a formatted persona reply."""

    reply_text = compose_reply(
        request.persona,
        request.conversation_state,
        intent=request.intent,
    )
    return ComposeResponse(persona=request.persona, intent=request.intent, reply=reply_text)


def lambda_handler(event: dict[str, Any], _context: Any | None = None) -> dict[str, Any]:
    """Entry point compatible with AWS Lambda."""

    try:
        request = ComposeRequest.model_validate(event)
    except ValidationError as exc:
        logger.error("Invalid Supervisor compose payload: %s", exc)
        raise

    response = render_reply(request)
    return response.model_dump()


__all__ = ["ComposeRequest", "ComposeResponse", "lambda_handler", "render_reply"]
