"""Language reference cards: the "<Language> Language Reference" section of the
paper's per-language prompt (vendored unmodified in ``esoforge/upstream/prompts``)."""

from __future__ import annotations

from .upstream import UPSTREAM_DIR

_MARKER = "Language Reference"


def card_for(language: str) -> str:
    text = (UPSTREAM_DIR / "prompts" / f"{language}.md").read_text()
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("## ") and _MARKER in ln)
    return "\n".join(lines[start:]).strip() + "\n"


def official_prompt(language: str) -> str:
    return (UPSTREAM_DIR / "prompts" / f"{language}.md").read_text()
