from __future__ import annotations

import warnings

import pytest

warnings.filterwarnings(
    "ignore",
    message="These events have been moved to production",
    category=DeprecationWarning,
    module=r"strands\.experimental\.hooks",
)


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure required env vars exist during tests."""

    monkeypatch.setenv("SEARCHAPI_KEY", "test-searchapi-key")
