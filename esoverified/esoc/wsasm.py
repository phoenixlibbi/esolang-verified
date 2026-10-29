"""Whitespace assembler: (op, arg) pairs -> Whitespace source text.

Ops: push n, dup, swap, discard, copy n, slide n, add, sub, mul, div, mod, store,
retrieve, out_char, out_num, read_char, read_num, label L, call L, jump L, jz L, jn L,
ret, end. Labels may be any string; they are mapped to unique binary label codes.
"""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

S, T, L = " ", "\t", "\n"

_SIMPLE = {
    "dup": S + L + S, "swap": S + L + T, "discard": S + L + L,
    "add": T + S + S + S, "sub": T + S + S + T, "mul": T + S + S + L,
    "div": T + S + T + S, "mod": T + S + T + T,
    "store": T + T + S, "retrieve": T + T + T,
    "out_char": T + L + S + S, "out_num": T + L + S + T,
    "read_char": T + L + T + S, "read_num": T + L + T + T,
    "ret": L + T + L, "end": L + L + L,
}
_WITH_NUM = {"push": S + S, "copy": S + T + S, "slide": S + T + L}
_WITH_LABEL = {"label": L + S + S, "call": L + S + T, "jump": L + S + L, "jz": L + T + S, "jn": L + T + T}


def number(n: int) -> str:
    sign = T if n < 0 else S
    bits = bin(abs(n))[2:] if n else ""
    return sign + bits.replace("0", S).replace("1", T) + L


def assemble(program: Iterable[Tuple[str, object]]) -> str:
    codes: Dict[object, str] = {}

    def label_code(name: object) -> str:
        if name not in codes:
            k = len(codes) + 1
            codes[name] = bin(k)[2:].replace("0", S).replace("1", T) + L
        return codes[name]

    parts = []
    for item in program:
        op, arg = item if len(item) == 2 else (item[0], None)  # type: ignore[misc]
        if op in _SIMPLE:
            parts.append(_SIMPLE[op])
        elif op in _WITH_NUM:
            parts.append(_WITH_NUM[op] + number(int(arg)))  # type: ignore[arg-type]
        elif op in _WITH_LABEL:
            parts.append(_WITH_LABEL[op] + label_code(arg))
        else:
            raise ValueError(f"unknown Whitespace op {op!r}")
    return "".join(parts)


def visible(src: str) -> str:
    """Render Whitespace with S/T/L letters (for docs and debugging)."""
    return src.replace(" ", "S").replace("\t", "T").replace("\n", "L")
