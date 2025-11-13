"""Persona instruction helpers."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_PERSONA_DOCS = {
    "paula": "paula.md",
    "gina": "gina.md",
    "bianca": "bianca.md",
}


def _persona_doc_path(persona: str) -> Path:
    docs_dir = Path(__file__).resolve().parent.parent / "docs"
    filename = _PERSONA_DOCS[persona.lower()]
    return docs_dir / filename


@lru_cache
def load_persona_instructions(persona: str) -> str:
    """Read the full Markdown instructions for the supplied persona."""

    path = _persona_doc_path(persona)
    return path.read_text(encoding="utf-8").strip()


def build_persona_prompt_block() -> str:
    """Return a concatenated persona instruction section for prompts."""

    sections = []
    for persona in ("paula", "gina", "bianca"):
        sections.append(
            f"### {persona.upper()} INSTRUCTIONS ###\n{load_persona_instructions(persona)}"
        )
    return "\n\n".join(sections)


PERSONA_PROMPT_BLOCK = build_persona_prompt_block()


__all__ = ["PERSONA_PROMPT_BLOCK", "load_persona_instructions"]
