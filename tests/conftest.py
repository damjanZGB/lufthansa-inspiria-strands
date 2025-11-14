from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure required env vars exist during tests."""

    monkeypatch.setenv("SEARCHAPI_KEY", "test-searchapi-key")
