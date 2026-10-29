"""Unmodified interpreters and harness from the paper's public code release.

Source: github.com/Lossfunk/esolang-metaprogramming @ b93ef26f1ff0c08a957c0ecc8397f21eb9ec247d
(benchmark_harness/interpreters/*.py and benchmark_harness/harness.py), MIT licence (LICENSE here).
They are the grading ground truth for "official" mode. Nothing in these files is edited;
`tests/test_upstream_pinned.py` checks their hashes.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Dict

UPSTREAM_DIR = Path(__file__).parent
UPSTREAM_COMMIT = "b93ef26f1ff0c08a957c0ecc8397f21eb9ec247d"
UPSTREAM_REPO = "https://github.com/Lossfunk/esolang-metaprogramming"

_MODULES = {
    "brainfuck": ("brainfuck_interpreter", "BrainfuckInterpreter"),
    "befunge98": ("befunge98_interpreter", "Befunge98Interpreter"),
    "whitespace": ("whitespace_interpreter", "WhitespaceInterpreter"),
}
_loaded: Dict[str, ModuleType] = {}


def _load(module_name: str) -> ModuleType:
    if module_name in _loaded:
        return _loaded[module_name]
    # The upstream files import `esolang_common` as a top-level module; load it under
    # that name once so they resolve it without editing their sources.
    if "esolang_common" not in sys.modules:
        spec = importlib.util.spec_from_file_location("esolang_common", UPSTREAM_DIR / "esolang_common.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["esolang_common"] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    name = f"esoforge_upstream_{module_name}"
    spec = importlib.util.spec_from_file_location(name, UPSTREAM_DIR / f"{module_name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses look the module up while the class is built
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    _loaded[module_name] = mod
    return mod


def official_interpreter(language: str, max_steps: int = 10_000_000):
    """Return an instance of the paper's interpreter for `language` (canonical key)."""
    module_name, cls_name = _MODULES[language]
    return getattr(_load(module_name), cls_name)(max_steps=max_steps)


def esolang_error_class():
    _load("brainfuck_interpreter")
    return sys.modules["esolang_common"].EsolangError
