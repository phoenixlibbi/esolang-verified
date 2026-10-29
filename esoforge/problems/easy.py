"""E01-E20: I/O and one-step arithmetic."""

from __future__ import annotations

from .util import LOWER, PRINTABLE, ints, line_text, lines, num, text, trunc_div, words
from . import register

VOWELS = set("aeiouAEIOU")


def _line(s: str) -> str:
    return lines(s)[0]


# E01 ------------------------------------------------------------------------
register("E01", lambda s: "Hello World!", lambda r: "", [""], "", {
    "no_bang": lambda s: "Hello World",
    "comma": lambda s: "Hello, World!",
})

# E02 ------------------------------------------------------------------------
register("E02", _line, lambda r: line_text(r, 0, 40), ["", " ", "a", "  lead", "trail  ", "x  y", PRINTABLE[:60]],
         "str_in ws_sensitive", {
    "first_word": lambda s: _line(s).split(" ")[0] if _line(s).strip() else _line(s),
    "drop_last_char": lambda s: _line(s)[:-1],
})

# E03 ------------------------------------------------------------------------
register("E03", lambda s: f"Hello, {_line(s)}!", lambda r: line_text(r, 1, 20),
         ["A", "Mary Ann", " x ", "O'Neil", "z" * 30], "str_in ws_sensitive", {
    "trimmed_name": lambda s: f"Hello, {_line(s).strip()}!",
    "no_comma": lambda s: f"Hello {_line(s)}!",
})

# E04 ------------------------------------------------------------------------
register("E04", lambda s: str(sum(ints(s))), lambda r: f"{num(r, -99999, 99999)} {num(r, -99999, 99999)}",
         ["0 0", "255 1", "128 128", "-1 1", "-256 -1", "99999 99999", "-99999 -99999", "-5 3", "1000 -1"],
         "int_in int_out neg_in", {
    "abs_sum": lambda s: str(sum(abs(v) for v in ints(s))),
    "sub": lambda s: str(ints(s)[0] - ints(s)[1]),
})

# E05 ------------------------------------------------------------------------
register("E05", lambda s: str(ints(s)[0] * ints(s)[1]), lambda r: f"{num(r, -9999, 9999)} {num(r, -9999, 9999)}",
         ["0 -5", "16 16", "-1 -1", "255 2", "-9999 9999", "1 -256", "100 100"], "int_in int_out neg_in", {
    "sign_lost": lambda s: str(abs(ints(s)[0] * ints(s)[1])),
    "add_instead": lambda s: str(sum(ints(s))),
})

# E06 ------------------------------------------------------------------------
register("E06", lambda s: "even" if ints(s)[0] % 2 == 0 else "odd", lambda r: str(num(r, -10 ** 6, 10 ** 6)),
         ["0", "-1", "-2", "255", "256", "-999999", "1000001"], "int_in neg_in", {
    # remainder with C semantics (-7 % 2 == -1) compared against 1: negatives become "even"
    "c_remainder": lambda s: "odd" if ints(s)[0] % 2 == 1 and ints(s)[0] > 0 else "even",
    "last_char_parity_only_for_one_digit": lambda s: "even" if int(s.strip()[-1]) % 2 == 0 else "odd",
})

# E07 ------------------------------------------------------------------------
register("E07", lambda s: str(len(_line(s))), lambda r: line_text(r, 0, 300),
         ["", " ", "   ", "a" * 255, "a" * 256, "x " * 150], "str_in int_out", {
    "no_spaces": lambda s: str(len(_line(s).replace(" ", ""))),
    "length_minus_one": lambda s: str(max(0, len(_line(s)) - 1)),
})

# E08 ------------------------------------------------------------------------
register("E08", lambda s: _line(s)[::-1], lambda r: line_text(r, 1, 40),
         ["a", "ab", " a", "a ", "abc def", "!@# $%"], "str_in ws_sensitive", {
    "reverse_words": lambda s: " ".join(_line(s).split(" ")[::-1]),
    "skip_first": lambda s: _line(s)[:0:-1],
})

# E09 ------------------------------------------------------------------------
register("E09", lambda s: str(sum(c in VOWELS for c in _line(s))), lambda r: line_text(r, 0, 60),
         ["", "AEIOUaeiou", "yYyY", "bcd", "a" * 300, "Queue"], "str_in int_out", {
    "lowercase_only": lambda s: str(sum(c in "aeiou" for c in _line(s))),
    "with_y": lambda s: str(sum(c in "aeiouyAEIOUY" for c in _line(s))),
})

# E10 ------------------------------------------------------------------------
register("E10", lambda s: str(ints(s)[0] * (ints(s)[0] + 1) // 2), lambda r: str(num(r, 0, 10000)),
         ["0", "1", "22", "23", "255", "10000"], "int_in int_out", {
    "to_n_minus_1": lambda s: str((ints(s)[0] - 1) * ints(s)[0] // 2),
    "n_squared_half": lambda s: str(ints(s)[0] ** 2 // 2),
})

# E11 ------------------------------------------------------------------------
def _digit_sum(s: str) -> str:
    return str(sum(int(c) for c in s.strip().lstrip("-")))


register("E11", _digit_sum, lambda r: str(num(r, -10 ** 9, 10 ** 9)),
         ["0", "-0", "-9", "999999999", "-1000000000", "29", "9999999"], "int_in int_out neg_in", {
    # '-' read as a digit: ord('-') - ord('0') = -3
    "minus_as_digit": lambda s: str(sum(ord(c) - 48 for c in s.strip())),
    "first_digits_only": lambda s: str(sum(int(c) for c in s.strip().lstrip("-")[:3])),
})

# E12 ------------------------------------------------------------------------
register("E12", lambda s: str(min(ints(s))), lambda r: f"{num(r, -9999, 9999)} {num(r, -9999, 9999)}",
         ["5 5", "-1 1", "-10 -9", "9 10", "100 -100", "255 256"], "int_in int_out neg_in", {
    "string_compare": lambda s: min(s.split()),
    "magnitude_compare": lambda s: str(min(ints(s), key=abs)),
})

# E13 ------------------------------------------------------------------------
register("E13", lambda s: str(max(ints(s))),
         lambda r: " ".join(str(num(r, -9999, 9999)) for _ in range(3)),
         ["-5 -6 -7", "0 0 0", "1 3 2", "3 1 2", "1 2 3", "9 10 8", "-1 -1 -2"], "int_in int_out neg_in", {
    "string_compare": lambda s: max(s.split()),
    "first_two_only": lambda s: str(max(ints(s)[:2])),
})

# E14 ------------------------------------------------------------------------
def _repeat(s: str) -> str:
    n, t = lines(s)[0], lines(s)[1]
    return t * int(n)


register("E14", _repeat, lambda r: f"{r.randint(0, 12)}\n{text(r, 1, 6, LOWER)}",
         ["0\nab", "1\nx", "10\nab", "12\nz", "3\na b"], "int_in multiline", {
    "one_digit_n": lambda s: lines(s)[1] * int(lines(s)[0][0]),
    "n_minus_1": lambda s: lines(s)[1] * max(0, int(lines(s)[0]) - 1),
})

# E15 ------------------------------------------------------------------------
register("E15", lambda s: f"{lines(s)[0]} {lines(s)[1]}",
         lambda r: f"{line_text(r, 1, 15)}\n{line_text(r, 1, 15)}",
         ["a\nb", "x y\nz", "  \nq", "p\n  r"], "str_in multiline ws_sensitive", {
    "no_space": lambda s: lines(s)[0] + lines(s)[1],
    "trimmed_lines": lambda s: f"{lines(s)[0].strip()} {lines(s)[1].strip()}",
})

# E16 ------------------------------------------------------------------------
register("E16", lambda s: f"{_line(s)[0]} {_line(s)[-1]}", lambda r: line_text(r, 1, 30).replace(" ", "_") or "a",
         ["a", "ab", "aba", "1234567890"], "str_in", {
    "second_last": lambda s: f"{_line(s)[0]} {_line(s)[-2] if len(_line(s)) > 1 else _line(s)[0]}",
    "first_twice": lambda s: f"{_line(s)[0]} {_line(s)[0]}",
})

# E17 ------------------------------------------------------------------------
register("E17", lambda s: "".join(c.upper() if "a" <= c <= "z" else c for c in _line(s)),
         lambda r: line_text(r, 1, 40), ["{|}~", "a{b}c", "already UP", "z`a"], "str_in ws_sensitive", {
    # 'c >= a then c - 32' without the upper bound breaks { | } ~
    "no_upper_bound": lambda s: "".join(chr(ord(c) - 32) if c >= "a" else c for c in _line(s)),
    # 'c > a' off by one leaves 'a' (and shifts the backtick)
    "lower_bound_off_by_one": lambda s: "".join(chr(ord(c) - 32) if "`" <= c <= "z" and c != "a" else c
                                                for c in _line(s)),
})

# E18 ------------------------------------------------------------------------
register("E18", lambda s: str(_line(s).count(" ")), lambda r: line_text(r, 0, 40, "ab  c d"),
         ["", " ", "     ", "a  b", " " * 300], "str_in int_out", {
    "words_minus_one": lambda s: str(max(0, len(_line(s).split()) - 1)),
    # counts runs of spaces instead of spaces
    "runs_of_spaces": lambda s: str(sum(1 for i, c in enumerate(_line(s))
                                        if c == " " and (i == 0 or _line(s)[i - 1] != " "))),
})

# E19 ------------------------------------------------------------------------
register("E19", lambda s: str(trunc_div(sum(ints(s)), 2)), lambda r: f"{num(r, -99999, 99999)} {num(r, -99999, 99999)}",
         ["-1 0", "-3 0", "-5 2", "1 -2", "-1 -2", "255 256", "99999 99999"], "int_in int_out neg_in", {
    "floor_division": lambda s: str(sum(ints(s)) // 2),
    "round_half_up": lambda s: str((sum(ints(s)) + 1) // 2),
})

# E20 ------------------------------------------------------------------------
def _cmp(s: str) -> str:
    a, b = ints(s)
    return "less" if a < b else "greater" if a > b else "equal"


register("E20", _cmp, lambda r: f"{num(r, -9999, 9999)} {num(r, -9999, 9999)}",
         ["-1 1", "1 -1", "-5 -6", "0 0", "-0 0", "256 0", "10 9"], "int_in neg_in", {
    "magnitude_compare": lambda s: (lambda a, b: "less" if a < b else "greater" if a > b else "equal")(
        *[abs(v) for v in ints(s)]),
    "string_compare": lambda s: (lambda a, b: "less" if a < b else "greater" if a > b else "equal")(*s.split()),
})
