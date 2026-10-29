"""Small helpers shared by the problem specs."""

from __future__ import annotations

import random
import string
from typing import List

PRINTABLE = string.ascii_letters + string.digits + " !\"#$%&'()*+,-./:;<=>?@[]^_`{|}~"
WORDCHARS = string.ascii_letters + string.digits
LOWER = string.ascii_lowercase


def ints(s: str) -> List[int]:
    return [int(t) for t in s.split()]


def lines(s: str) -> List[str]:
    return s.split("\n")


def text(rng: random.Random, lo: int, hi: int, alphabet: str = PRINTABLE) -> str:
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(lo, hi)))


def line_text(rng: random.Random, lo: int, hi: int, alphabet: str = PRINTABLE) -> str:
    """Text for a single line (never contains a newline)."""
    return text(rng, lo, hi, alphabet)


def num(rng: random.Random, lo: int, hi: int) -> int:
    """Integer in [lo, hi] biased toward interesting magnitudes (0, 1, 255/256, ...)."""
    r = rng.random()
    if r < 0.15:
        cands = [v for v in (0, 1, -1, 9, 10, 99, 100, 127, 128, 255, 256, 257, 999, 1000, -255, -256)
                 if lo <= v <= hi]
        if cands:
            return rng.choice(cands)
    if r < 0.5:
        # log-uniform magnitude
        top = max(abs(lo), abs(hi))
        mag = int(10 ** (rng.random() * len(str(top))))
        v = mag if rng.random() < 0.5 or lo >= 0 else -mag
        if lo <= v <= hi:
            return v
    return rng.randint(lo, hi)


def words(rng: random.Random, n_lo: int, n_hi: int, w_lo: int = 1, w_hi: int = 8,
          alphabet: str = LOWER) -> str:
    return " ".join(text(rng, w_lo, w_hi, alphabet) for _ in range(rng.randint(n_lo, n_hi)))


def trunc_div(a: int, b: int) -> int:
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q
