from __future__ import annotations

import types

from scripts import chat_agent


def test_parse_args_defaults_to_none() -> None:
    args = chat_agent.parse_args([])
    assert args.persona is None


class DummyAgent:
    def __init__(self) -> None:
        self.persona = None
        self.state = types.SimpleNamespace(set=self._set_state)

    def _set_state(self, key: str, value: str) -> None:
        setattr(self, key, value)


def test_build_agent_seeds_persona(monkeypatch) -> None:
    dummy = DummyAgent()

    def fake_builder():
        return dummy

    monkeypatch.setattr(chat_agent, "build_supervisor_agent", fake_builder)

    agent = chat_agent.build_agent("Gina")
    assert agent.persona == "gina"


def test_build_agent_handles_missing_persona(monkeypatch) -> None:
    dummy = DummyAgent()

    def fake_builder():
        return dummy

    monkeypatch.setattr(chat_agent, "build_supervisor_agent", fake_builder)

    agent = chat_agent.build_agent(None)
    assert agent.persona is None
