"""EsoLang Env Forge: verified, contamination-resistant RL environments and a
model-free audit toolkit for EsoLang-Bench style unfamiliar-language tasks."""

__version__ = "0.1.0"

LANGUAGES = ("brainfuck", "befunge98", "whitespace")
EXTENSIONS = {"brainfuck": ".bf", "befunge98": ".b98", "whitespace": ".ws"}
_ALIASES = {
    "bf": "brainfuck", "brainfuck": "brainfuck",
    "b98": "befunge98", "befunge98": "befunge98", "befunge-98": "befunge98", "befunge": "befunge98",
    "ws": "whitespace", "whitespace": "whitespace",
}


def canonical_language(name: str) -> str:
    """Map 'bf', 'befunge-98', 'WS', ... to the canonical language key."""
    key = name.strip().lower()
    if key not in _ALIASES:
        raise ValueError(f"unknown language {name!r}; choose from {', '.join(LANGUAGES)}")
    return _ALIASES[key]
