"""M01-M20: list and string operations."""

from __future__ import annotations

from .util import LOWER, PRINTABLE, ints, line_text, lines, num, text, words
from . import register

VOWELS = set("aeiouAEIOU")


def _line(s: str) -> str:
    return lines(s)[0]


def _n_then_list(r, n_lo: int, n_hi: int, lo: int, hi: int) -> str:
    n = r.randint(n_lo, n_hi)
    return f"{n}\n" + " ".join(str(num(r, lo, hi)) for _ in range(n))


def _list(s: str):
    return ints(lines(s)[1])


# M01 ------------------------------------------------------------------------
def _pal_gen(r) -> str:
    half = line_text(r, 1, 10, PRINTABLE.replace(" ", "") + "  ")
    if r.random() < 0.5:
        return half + (r.choice(PRINTABLE) if r.random() < 0.5 else "") + half[::-1]
    return line_text(r, 1, 20)


register("M01", lambda s: "yes" if _line(s) == _line(s)[::-1] else "no", _pal_gen,
         ["Aa", "a a", "ab a", "abca", "x", "!@!", "Racecar", "noon", "abcdba"], "str_in", {
    "case_insensitive": lambda s: "yes" if _line(s).lower() == _line(s).lower()[::-1] else "no",
    "ends_only": lambda s: "yes" if _line(s)[0] == _line(s)[-1] else "no",
})

# M02 ------------------------------------------------------------------------
register("M02", lambda s: str(len(_line(s).split(" "))), lambda r: words(r, 1, 40),
         ["a", "a b", "x " * 299 + "x", "ab cd ef gh"], "str_in int_out", {
    "count_spaces": lambda s: str(_line(s).count(" ")),
    "count_letters_div": lambda s: str(len(_line(s).replace(" ", "")) // 2 or 1),
})

# M03 ------------------------------------------------------------------------
def _rle(t: str, cap=None, digit_mod=False) -> str:
    out = []
    i = 0
    while i < len(t):
        j = i
        while j < len(t) and t[j] == t[i]:
            j += 1
        k = j - i
        if cap:
            while k > cap:
                out.append(f"{t[i]}{cap}")
                k -= cap
        out.append(f"{t[i]}{k % 10 if digit_mod else k}")
        i = j
    return "".join(out)


def _rle_gen(r) -> str:
    return "".join(r.choice(LOWER[:4]) * r.choice([1, 1, 2, 3, 9, 10, 11, 12, 15]) for _ in range(r.randint(1, 6)))


register("M03", lambda s: _rle(_line(s)), _rle_gen, ["a" * 10, "a" * 12 + "b", "ab" * 5, "z" * 99, "q"], "str_in", {
    "single_digit_counts": lambda s: _rle(_line(s), digit_mod=True),
    "runs_capped_at_9": lambda s: _rle(_line(s), cap=9),
})

# M04 ------------------------------------------------------------------------
register("M04", lambda s: "".join(chr((ord(c) - 97 + 3) % 26 + 97) for c in _line(s)),
         lambda r: text(r, 1, 30, LOWER), ["xyz", "w", "abcdefghijklmnopqrstuvwxyz"], "str_in", {
    "no_wrap": lambda s: "".join(chr(ord(c) + 3) for c in _line(s)),
    "wrap_to_b": lambda s: "".join(chr((ord(c) - 97 + 3) % 25 + 97) for c in _line(s)),
})

# M05 ------------------------------------------------------------------------
def _binexpr(s: str) -> str:
    a, op, b = _line(s).split(" ")
    x, y = int(a), int(b)
    return str(x + y if op == "+" else x - y if op == "-" else x * y)


register("M05", _binexpr, lambda r: f"{num(r, -1000, 1000)} {r.choice('+-*')} {num(r, -1000, 1000)}",
         ["-5 - -5", "0 * -7", "-1000 * -1000", "255 + 1", "3 - 10", "-3 + -4"], "int_in int_out neg_in", {
    "minus_reversed": lambda s: (lambda a, op, b: str(int(a) + int(b) if op == "+" else int(b) - int(a)
                                                      if op == "-" else int(a) * int(b)))(*_line(s).split(" ")),
    "left_sign_dropped": lambda s: (lambda a, op, b: _binexpr(f"{a.lstrip('-')} {op} {b}"))(*_line(s).split(" ")),
})

# M06 ------------------------------------------------------------------------
def _gcd(a: int, b: int) -> int:
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def _gcd_c(a: int, b: int) -> int:
    # Euclid with C-style remainder (sign of dividend) and no final abs()
    while b:
        r = abs(a) % abs(b)
        a, b = b, (r if a >= 0 else -r)
    return a


register("M06", lambda s: str(_gcd(*ints(s))), lambda r: f"{num(r, 1, 10 ** 6)} {num(r, 1, 10 ** 6)}",
         ["1 1", "0 7", "7 0", "-12 18", "12 -18", "-4 -6", "256 512", "1000000 999999"], "int_in int_out neg_in", {
    "c_remainder_sign": lambda s: str(_gcd_c(*ints(s))),
    "min_of_two": lambda s: str(min(abs(v) for v in ints(s))),
})

# M07 ------------------------------------------------------------------------
def _fact(n: int) -> int:
    f = 1
    for i in range(2, n + 1):
        f *= i
    return f


register("M07", lambda s: str(_fact(ints(s)[0])), lambda r: str(r.randint(0, 10)),
         [str(n) for n in range(11)], "int_in int_out", {
    "zero_fact_is_zero": lambda s: "0" if ints(s)[0] == 0 else str(_fact(ints(s)[0])),
    "16bit": lambda s: str(_fact(ints(s)[0]) % 65536),
})

# M08 ------------------------------------------------------------------------
def _fib(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


register("M08", lambda s: str(_fib(ints(s)[0])), lambda r: str(r.randint(1, 90)),
         ["1", "2", "13", "14", "47", "48", "90"], "int_in int_out", {
    "zero_indexed": lambda s: str(_fib(ints(s)[0] - 1)),
    "u32_overflow": lambda s: str(_fib(ints(s)[0]) % 2 ** 32),
})

# M09 ------------------------------------------------------------------------
register("M09", lambda s: bin(ints(s)[0])[2:], lambda r: str(num(r, 0, 10 ** 9)),
         ["0", "1", "2", "255", "256", "1023", "1000000000"], "int_in", {
    "zero_empty": lambda s: bin(ints(s)[0])[2:] if ints(s)[0] else "",
    "lsb_first": lambda s: bin(ints(s)[0])[2:][::-1],
})

# M10 ------------------------------------------------------------------------
register("M10", lambda s: str(int(_line(s), 2)), lambda r: "1" + text(r, 0, 39, "01") if r.random() < .9 else "0",
         ["0", "1", "100000000", "111111111", "0001", "1" * 40], "int_out", {
    "last_8_bits": lambda s: str(int(_line(s)[-8:], 2)),
    "msb_last": lambda s: str(int(_line(s)[::-1], 2)),
})

# M11 ------------------------------------------------------------------------
def _occ(s: str, overlap=True) -> str:
    t, p = lines(s)[0], lines(s)[1]
    if not overlap:
        return str(t.count(p))
    return str(sum(1 for i in range(len(t) - len(p) + 1) if t[i:i + len(p)] == p))


def _occ_gen(r) -> str:
    alpha = "ab" if r.random() < 0.6 else LOWER[:5]
    return f"{text(r, 1, 40, alpha)}\n{text(r, 1, 3, alpha)}"


register("M11", _occ, _occ_gen, ["aaaa\naaa", "ab\nabc", "aaaaaaaaaaaa\naa", "abab\nb"], "str_in multiline int_out", {
    "non_overlapping": lambda s: _occ(s, overlap=False),
    "first_char_only": lambda s: str(lines(s)[0].count(lines(s)[1][0])),
})

# M12 ------------------------------------------------------------------------
register("M12", lambda s: "".join(c for c in _line(s) if c not in VOWELS), lambda r: line_text(r, 1, 40),
         ["AEIOUaeiou", "yYy", "Ab Eb", "u"], "str_in ws_sensitive", {
    "lowercase_vowels_only": lambda s: "".join(c for c in _line(s) if c not in "aeiou"),
    "drops_y_too": lambda s: "".join(c for c in _line(s) if c not in "aeiouyAEIOUY"),
})

# M13 ------------------------------------------------------------------------
register("M13", lambda s: " ".join(map(str, sorted(_list(s)))), lambda r: _n_then_list(r, 1, 15, -999, 999),
         ["2\n10 9", "3\n-1 -10 2", "4\n100 20 3 -400", "5\n7 7 -7 0 7", "2\n256 255"], "int_in neg_in multiline", {
    "string_sort": lambda s: " ".join(sorted(lines(s)[1].split())),
    "magnitude_sort": lambda s: " ".join(map(str, sorted(_list(s), key=abs))),
})

# M14 ------------------------------------------------------------------------
def _m14_gen(r) -> str:
    vals = [num(r, -999, 999) for _ in range(r.randint(2, 12))]
    if r.random() < 0.4:  # duplicates of the maximum
        vals += [max(vals)] * r.randint(1, 3)
    if len(set(vals)) < 2:
        vals.append(vals[0] + 1)
    r.shuffle(vals)
    return f"{len(vals)}\n" + " ".join(map(str, vals))


register("M14", lambda s: str(sorted(set(_list(s)))[-2]), _m14_gen,
         ["3\n9 9 8", "4\n5 5 5 4", "2\n-1 -2", "5\n1 9 9 9 9"], "int_in neg_in multiline", {
    "not_distinct": lambda s: str(sorted(_list(s))[-2]),
    "second_smallest": lambda s: str(sorted(set(_list(s)))[1]),
})

# M15 ------------------------------------------------------------------------
def _ana_gen(r) -> str:
    a = text(r, 1, 12, LOWER[:6])
    if r.random() < 0.5:
        b = "".join(r.sample(a, len(a)))
    else:
        b = list(a)
        b[r.randrange(len(b))] = r.choice(LOWER[:6])
        b = "".join(r.sample(b, len(b)))
    return f"{a}\n{b}"


register("M15", lambda s: "yes" if sorted(lines(s)[0]) == sorted(lines(s)[1]) else "no", _ana_gen,
         ["aab\nabb", "abc\nabcd", "aa\na", "abc\ncab"], "str_in multiline", {
    "same_letter_set": lambda s: "yes" if set(lines(s)[0]) == set(lines(s)[1]) else "no",
    "same_length": lambda s: "yes" if len(lines(s)[0]) == len(lines(s)[1]) else "no",
})

# M16 ------------------------------------------------------------------------
def _il_gen(r) -> str:
    n = r.randint(1, 15)
    return f"{text(r, n, n, LOWER)}\n{text(r, n, n, LOWER.upper() + '0123456789')}"


register("M16", lambda s: "".join(a + b for a, b in zip(lines(s)[0], lines(s)[1])), _il_gen,
         ["a\nB", "ab\nCD", "abcdefghij\nABCDEFGHIJ"], "str_in multiline", {
    "second_first": lambda s: "".join(b + a for a, b in zip(lines(s)[0], lines(s)[1])),
    "concat": lambda s: lines(s)[0] + lines(s)[1],
})

# M17 ------------------------------------------------------------------------
register("M17", lambda s: _line(s).replace(" ", "_"), lambda r: line_text(r, 1, 40, "ab  cd e"),
         [" ", "a  b", "  x  ", "nospace"], "str_in", {
    "collapse_runs": lambda s: "_".join(w for w in _line(s).split(" ") if w) if _line(s).strip() else "_",
    "first_only": lambda s: _line(s).replace(" ", "_", 1),
})

# M18 ------------------------------------------------------------------------
register("M18", lambda s: str(sum(_list(s))), lambda r: _n_then_list(r, 1, 20, -9999, 9999),
         ["1\n-1", "2\n255 1", "3\n-100 -100 -100", "4\n9999 9999 9999 9999"], "int_in int_out neg_in multiline", {
    "skip_last": lambda s: str(sum(_list(s)[:-1])),
    "abs_values": lambda s: str(sum(abs(v) for v in _list(s))),
})

# M19 ------------------------------------------------------------------------
register("M19", lambda s: _line(s)[::2], lambda r: line_text(r, 1, 40),
         ["a", "ab", "abc", "a b c d", " ab", "  x"], "str_in ws_sensitive", {
    "odd_indices": lambda s: _line(s)[1::2],
    "one_based": lambda s: _line(s)[1::2] or _line(s)[:1],
})

# M20 ------------------------------------------------------------------------
register("M20", lambda s: str(len(set(_line(s)))), lambda r: line_text(r, 1, 60),
         ["aA", "  ", "abcabcabc", PRINTABLE], "str_in int_out", {
    "case_insensitive": lambda s: str(len(set(_line(s).lower()))),
    "count_singletons": lambda s: str(sum(1 for c in set(_line(s)) if _line(s).count(c) == 1)),
})
