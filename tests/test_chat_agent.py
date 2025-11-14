from __future__ import annotations

import pytest

from scripts.chat_agent import AGENT_FACTORIES, parse_args, resolve_agent_factory


def test_resolve_agent_factory_is_case_insensitive() -> None:
    factory = resolve_agent_factory("Supervisor")
    assert callable(factory)


def test_resolve_agent_factory_rejects_unknown_agent() -> None:
    with pytest.raises(ValueError):
        resolve_agent_factory("unknown")


def test_parse_args_defaults_to_supervisor() -> None:
    args = parse_args([])
    assert args.agent == "supervisor"
    assert set(args.__dict__) == {"agent", "persona"}


def test_agent_registry_has_expected_members() -> None:
    expected = {"supervisor", "flight_search", "destination_scout"}
    assert expected.issubset(set(AGENT_FACTORIES))
