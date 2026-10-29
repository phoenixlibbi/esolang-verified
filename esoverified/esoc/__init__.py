"""esoc: a compiler from a small structured IR to Brainfuck, Befunge-98 and Whitespace.

The paper observes that the strongest agents write Python generators that emit the
target esolang instead of writing it by hand. esoc is that strategy as a tested tool:

    from esoverified.esoc import compile_problem
    source = compile_problem("E04", "befunge98")

Every program is checked against the reference solutions on the official tests and on
fresh suites, with the official interpreter semantics and step cap.
"""

from __future__ import annotations

from .. import canonical_language
from .ir import Program


def compile_program(prog: Program, language: str) -> str:
    lang = canonical_language(language)
    if lang == "whitespace":
        from .ws import compile_ws
        return compile_ws(prog)
    if lang == "befunge98":
        from .b98 import compile_b98
        return compile_b98(prog)
    from .bf import compile_bf
    return compile_bf(prog)


def compile_problem(pid: str, language: str) -> str:
    from .programs import build
    return compile_program(build(pid), language)


__all__ = ["compile_program", "compile_problem", "Program"]
