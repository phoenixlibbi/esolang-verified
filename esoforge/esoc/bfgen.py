"""Tiny Brainfuck snippets that do not need the full compiler."""

from __future__ import annotations


def print_text(text: str) -> str:
    """A program that prints `text` (code points 0..255) using one cell."""
    out = []
    cur = 0
    for ch in text:
        v = ord(ch)
        if v > 255:
            raise ValueError("Brainfuck cells hold bytes; cannot print code points above 255")
        d = (v - cur) % 256
        out.append("+" * d if d <= 128 else "-" * (256 - d))
        out.append(".")
        cur = v
    return "".join(out)
