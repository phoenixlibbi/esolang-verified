"""Fast, independent interpreters for Brainfuck, Befunge-98 and Whitespace.

Each interpreter has two dialects:

* ``official``: reproduces the paper's interpreters exactly, including step counting,
  so a program that passes here passes the official grader (checked by differential
  tests against the vendored upstream code).
* ``spec``: follows the language specification where the official interpreter deviates
  (exact integer division, unbounded Befunge fungespace with integer cells, ...).

Comparing the two dialects shows which programs depend on interpreter quirks.
"""

from __future__ import annotations

from .common import EsoError, StepLimitExceeded, InputBuffer, RunResult, run
from . import bf, b98, ws

__all__ = ["EsoError", "StepLimitExceeded", "InputBuffer", "RunResult", "run", "bf", "b98", "ws"]
