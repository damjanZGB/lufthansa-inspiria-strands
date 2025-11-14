"""Centralised configuration for the Inspiria Strands workspace."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven settings shared across agents."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bedrock_model_id: str = Field(
        "anthropic.claude-3-haiku-20240307-v1:0",
        validation_alias=AliasChoices("BEDROCK_MODEL_ID"),
    )
    bedrock_region: str = Field(
        "us-east-1",
        validation_alias=AliasChoices("AWS_REGION"),
    )
    bedrock_temperature: float = Field(0.2, ge=0.0, le=1.0)
    bedrock_max_tokens: int = Field(4096, ge=512, le=8192)

    searchapi_endpoint: HttpUrl = Field(
        "https://www.searchapi.io/api/v1/search",
        validation_alias=AliasChoices("SEARCHAPI_ENDPOINT"),
    )
    searchapi_key: str = Field(
        ...,
        validation_alias=AliasChoices("SEARCHAPI_KEY"),
        description="SearchAPI bearer token used by http_request calls.",
    )
    open_meteo_endpoint: HttpUrl = Field(
        "https://api.open-meteo.com/v1/forecast",
        validation_alias=AliasChoices("OPEN_METEO_ENDPOINT"),
        description="Open-Meteo forecast endpoint for weather snapshots.",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
