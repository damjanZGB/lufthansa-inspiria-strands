#!/usr/bin/env python3
"""Interactive CLI for chatting with the Inspiria Supervisor agent."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

from strands import Agent

from supervisor.agent import build_agent as build_supervisor_agent

PERSONA_OPENERS = {
    "paula": "Hi, I am Paula. Here's what I gathered for you:",
    "gina": "Gina here — tailored insights coming your way:",
    "bianca": "Bianca speaking with a spark of inspiration:",
}


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Return CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Chat with the Lufthansa Inspiria supervisor (sub-agents stay hidden)."
    )
    parser.add_argument(
        "--persona",
        default=None,
        help="Optional persona identifier stored in the supervisor state.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose logging to help diagnose tool/model issues.",
    )
    return parser.parse_args(args=args)


def build_agent(persona: str | None = None) -> Agent:
    """Instantiate the supervisor agent and seed persona state if provided."""

    agent = build_supervisor_agent()
    if persona:
        agent.state.set("persona", persona.lower())
    return agent


def interactive_loop(agent: Agent, persona: str | None = None) -> None:
    """Prompt the user for input until they exit."""

    print("--------------------------------------------------------------------")
    print("Connected to the Lufthansa Inspiria supervisor.")
    print("Type messages to interact, or 'exit' to quit.")
    print("--------------------------------------------------------------------\n")

    intro_needed = bool(persona and persona.lower() in PERSONA_OPENERS)
    persona_key = persona.lower() if persona else None

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

        if intro_needed:
            print(f"\n{PERSONA_OPENERS[persona_key]}\n")
            intro_needed = False

        try:
            response = agent(user_input)
        except Exception as exc:  # pragma: no cover - network/model errors
            print(f"[error] {exc}")
            continue

        if response is not None:
            print(f"\nsupervisor> {response}\n")


def main(raw_args: list[str] | None = None) -> None:
    """CLI entry point."""

    if load_dotenv:
        load_dotenv()
    os.environ.setdefault("STRANDS_TOOL_CONSOLE_MODE", "enabled")

    args = parse_args(raw_args)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    agent = build_agent(args.persona)
    interactive_loop(agent, args.persona)


if __name__ == "__main__":
    main()
