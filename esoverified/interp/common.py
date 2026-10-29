"""Shared pieces for the interpreters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

DEFAULT_MAX_STEPS = 10_000_000  # the paper's MAX_INTERPRETER_STEPS

# Kept here (not imported from the package) so this directory works standalone inside
# Harbor task images.
_ALIASES = {"bf": "brainfuck", "brainfuck": "brainfuck", "b98": "befunge98", "befunge98": "befunge98",
            "befunge-98": "befunge98", "befunge": "befunge98", "ws": "whitespace", "whitespace": "whitespace"}


class EsoError(Exception):
    """A runtime or syntax error raised by a program (not by the interpreter itself)."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(f"{kind}: {message}")
        self.kind = kind
        self.message = message


class StepLimitExceeded(EsoError):
    def __init__(self, max_steps: int) -> None:
        super().__init__("StepLimitExceeded", f"Execution exceeded {max_steps} steps.")


class InputBuffer:
    """Same input semantics as the official interpreters (esolang_common.InputBuffer)."""

    __slots__ = ("data", "index")

    def __init__(self, data: str) -> None:
        self.data = data
        self.index = 0

    def read_char(self) -> Optional[str]:
        if self.index >= len(self.data):
            return None
        ch = self.data[self.index]
        self.index += 1
        return ch

    def read_int(self) -> Optional[int]:
        data, n = self.data, len(self.data)
        while self.index < n and data[self.index].isspace():
            self.index += 1
        if self.index >= n:
            return None
        start = self.index
        if data[self.index] in "+-":
            self.index += 1
        while self.index < n and data[self.index].isdigit():
            self.index += 1
        token = data[start:self.index]
        if token in ("", "+", "-"):
            self.index = start
            return None
        try:
            return int(token)
        except ValueError:  # e.g. non-ASCII digits that int() rejects
            self.index = start
            return None


@dataclass
class RunResult:
    output: Optional[str]          # None when the program raised an error
    error: Optional[str] = None    # "Kind: message"
    steps: int = 0

    @property
    def ok(self) -> bool:
        return self.error is None


def run(language: str, program: str, input_data: str = "", *, dialect: str = "official",
        max_steps: int = DEFAULT_MAX_STEPS) -> RunResult:
    """Run `program` and capture output or error. Never raises for program faults."""
    from . import bf, b98, ws  # local import: avoid cycles
    lang = _ALIASES.get(language.strip().lower())
    if lang is None:
        raise ValueError(f"unknown language {language!r}")
    impl = {"brainfuck": bf, "befunge98": b98, "whitespace": ws}[lang]
    try:
        out, steps = impl.execute(program, input_data, dialect=dialect, max_steps=max_steps)
        return RunResult(out, None, steps)
    except EsoError as e:
        return RunResult(None, f"{e.kind}: {e.message}", 0)
    except RecursionError:
        return RunResult(None, "RuntimeError: recursion limit", 0)
