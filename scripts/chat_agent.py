#!/usr/bin/env python3
"""Interactive CLI for chatting with Inspiria Strands agents."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

from strands import Agent

from destination_scout.agent import build_agent as build_destination_scout_agent
from flight_search.agent import build_agent as build_flight_search_agent
from supervisor.agent import build_agent as build_supervisor_agent

AGENT_FACTORIES: dict[str, Callable[[], Agent]] = {
    "supervisor": build_supervisor_agent,
    "flight_search": build_flight_search_agent,
    "destination_scout": build_destination_scout_agent,
}


def resolve_agent_factory(name: str) -> Callable[[], Agent]:
    """Return the registered agent factory for the supplied name."""

    key = name.lower()
    if key not in AGENT_FACTORIES:
        options = ", ".join(sorted(AGENT_FACTORIES))
        raise ValueError(f"Unknown agent '{name}'. Choose one of: {options}")
    return AGENT_FACTORIES[key]


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Return CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Chat with Lufthansa Inspiria Strands agents (Supervisor, Flight Search, Destination Scout)."
    )
    parser.add_argument(
        "--agent",
        default="supervisor",
        choices=sorted(AGENT_FACTORIES),
        help="Agent name to instantiate.",
    )
    parser.add_argument(
        "--persona",
        default=None,
        help="Optional persona identifier stored in the agent state (Supervisor only).",
    )
    return parser.parse_args(args=args)


def build_agent(agent_name: str, persona: str | None = None) -> Agent:
    """Instantiate the requested Strands agent and seed persona state if provided."""

    factory = resolve_agent_factory(agent_name)
    agent = factory()
    if persona and agent_name == "supervisor":
        agent.state["persona"] = persona.lower()
    return agent


def interactive_loop(agent: Agent, agent_name: str) -> None:
    """Prompt the user for input until they exit."""

    print("--------------------------------------------------------------------")
    print(f"Connected to {agent_name.replace('_', ' ').title()} agent.")
    print("Type messages to interact, or 'exit' to quit.")
    print("--------------------------------------------------------------------\n")

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting…")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye 👋")
            break

        try:
            response = agent(user_input)
        except Exception as exc:  # pragma: no cover - network/model errors
            print(f"[error] {exc}")
            continue

        if response is not None:
            print(f"\n{agent_name}> {response}\n")


def main(raw_args: list[str] | None = None) -> None:
    """CLI entry point."""

    if load_dotenv:
        load_dotenv()
    os.environ.setdefault("STRANDS_TOOL_CONSOLE_MODE", "enabled")

    args = parse_args(raw_args)
    agent = build_agent(args.agent, args.persona)
    interactive_loop(agent, args.agent)


if __name__ == "__main__":
    main()
