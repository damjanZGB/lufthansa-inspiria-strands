"""Centralised configuration for the Inspiria Strands workspace."""

from __future__ import annotations

from functools import lru_cache

from pydantic import BaseSettings, Field, HttpUrl


class Settings(BaseSettings):
    """Environment-driven settings shared across agents."""

    bedrock_model_id: str = Field(
        "anthropic.claude-3-5-sonnet-20241022-v2:0", env="BEDROCK_MODEL_ID"
    )
    bedrock_region: str = Field("us-west-2", env="AWS_REGION")
    bedrock_temperature: float = Field(0.2, ge=0.0, le=1.0)
    bedrock_max_tokens: int = Field(4096, ge=512, le=8192)

    searchapi_endpoint: HttpUrl = Field(
        "https://www.searchapi.io/api/v1/search", env="SEARCHAPI_ENDPOINT"
    )
    searchapi_key: str = Field(
        ...,
        env="SEARCHAPI_KEY",
        description="SearchAPI bearer token used by http_request calls.",
    )
    open_meteo_endpoint: HttpUrl = Field(
        "https://api.open-meteo.com/v1/forecast",
        env="OPEN_METEO_ENDPOINT",
        description="Open-Meteo forecast endpoint for weather snapshots.",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
