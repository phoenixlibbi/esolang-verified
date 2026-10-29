"""H01-H20: multi-step numeric and string manipulation."""

from __future__ import annotations

from .util import LOWER, PRINTABLE, ints, line_text, lines, num, text, trunc_div, words
from . import register


def _line(s: str) -> str:
    return lines(s)[0]


# H01 ------------------------------------------------------------------------
def _balanced(t: str, wrap: int = 0) -> bool:
    d = 0
    for c in t:
        d += 1 if c == "(" else -1
        if wrap:
            d %= wrap
        elif d < 0:
            return False
    return d == 0


def _paren_gen(r) -> str:
    if r.random() < 0.5:
        out, d = [], 0
        for _ in range(r.randint(0, 15)):
            if d and r.random() < 0.5:
                out.append(")")
                d -= 1
            else:
                out.append("(")
                d += 1
        return "".join(out) + ")" * d
    return text(r, 0, 30, "()")


register("H01", lambda s: "yes" if _balanced(_line(s)) else "no", _paren_gen,
         ["", ")(", "(()", "())(()", "()" * 150, "(" * 300 + ")" * 300, "(" * 256], "str_in", {
    "counts_only": lambda s: "yes" if _line(s).count("(") == _line(s).count(")") else "no",
    "byte_counter": lambda s: "yes" if _balanced(_line(s), wrap=256) else "no",
})

# H02 ------------------------------------------------------------------------
def _tokens(e: str):
    out, cur = [], ""
    for c in e:
        if c.isdigit():
            cur += c
        else:
            out += [int(cur), c]
            cur = ""
    return out + [int(cur)]


def _eval_prec(e: str) -> int:
    toks = _tokens(e)
    terms, ops = [toks[0]], []
    for op, v in zip(toks[1::2], toks[2::2]):
        if op == "*":
            terms[-1] *= v
        else:
            ops.append(op)
            terms.append(v)
    acc = terms[0]
    for op, v in zip(ops, terms[1:]):
        acc = acc + v if op == "+" else acc - v
    return acc


def _eval_ltr(e: str) -> int:
    toks = _tokens(e)
    acc = toks[0]
    for op, v in zip(toks[1::2], toks[2::2]):
        acc = acc + v if op == "+" else acc - v if op == "-" else acc * v
    return acc


def _eval_right_minus(e: str) -> int:
    # precedence for '*', but a - b + c parsed as a - (b + c)
    toks = _tokens(e)
    terms, ops = [toks[0]], []
    for op, v in zip(toks[1::2], toks[2::2]):
        if op == "*":
            terms[-1] *= v
        else:
            ops.append(op)
            terms.append(v)
    acc = terms[-1]
    for op, v in zip(reversed(ops), reversed(terms[:-1])):
        acc = v + acc if op == "+" else v - acc
    return acc


def _expr_gen(r) -> str:
    # at most 4 factors per product keeps every intermediate value below 2**46
    n = r.randint(1, 6)
    parts = [str(num(r, 1, 999))]
    chain = 1
    for _ in range(n - 1):
        op = r.choice("+-*") if chain < 4 else r.choice("+-")
        chain = chain + 1 if op == "*" else 1
        parts += [op, str(num(r, 1, 999))]
    return "".join(parts)


register("H02", lambda s: str(_eval_prec(_line(s))), _expr_gen,
         ["7", "1-2+3", "10-2-3", "2*3*4-100", "1+2*3*4+5", "999*999", "5-10*2"], "int_out", {
    "left_to_right": lambda s: str(_eval_ltr(_line(s))),
    "minus_right_assoc": lambda s: str(_eval_right_minus(_line(s))),
})

# H03 ------------------------------------------------------------------------
def _primes_upto(n: int):
    sieve = bytearray([1]) * (n + 1)
    sieve[:2] = b"\x00\x00"
    for i in range(2, int(n ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
    return [i for i in range(n + 1) if sieve[i]]


register("H03", lambda s: str(len(_primes_upto(ints(s)[0]))), lambda r: str(num(r, 2, 3000)),
         ["2", "3", "4", "1000", "1621", "3000"], "int_in int_out", {
    "exclusive_n": lambda s: str(len(_primes_upto(ints(s)[0] - 1))),
    "one_is_prime": lambda s: str(len(_primes_upto(ints(s)[0])) + 1),
})

# H04 ------------------------------------------------------------------------
_P = _primes_upto(5000)
register("H04", lambda s: str(_P[ints(s)[0] - 1]), lambda r: str(r.randint(1, 400)),
         ["1", "2", "54", "55", "400"], "int_in int_out", {
    "zero_indexed": lambda s: str(_P[ints(s)[0]]),
    "one_is_prime": lambda s: str(([1] + _P)[ints(s)[0] - 1]),
})

# H05 ------------------------------------------------------------------------
def _big(r) -> str:
    d = r.randint(1, 60)
    return str(r.randint(1, 9)) + text(r, d - 1, d - 1, "0123456789") if r.random() < 0.95 else "0"


register("H05", lambda s: str(int(lines(s)[0]) + int(lines(s)[1])), lambda r: f"{_big(r)}\n{_big(r)}",
         ["0\n0", "9" * 60 + "\n1", "1\n" + "9" * 40, "5\n5", "123456789012345678901234567890\n0"], "multiline", {
    "drop_final_carry": lambda s: str((int(lines(s)[0]) + int(lines(s)[1])) %
                                      10 ** max(len(lines(s)[0]), len(lines(s)[1]))),
    "u64": lambda s: str((int(lines(s)[0]) + int(lines(s)[1])) % 2 ** 64),
})

# H06 ------------------------------------------------------------------------
register("H06", lambda s: max(_line(s).split(" "), key=len), lambda r: words(r, 1, 12, 1, 10),
         ["a", "ab cd", "abc de fgh", "x yy zz w"], "str_in", {
    "last_of_ties": lambda s: max(reversed(_line(s).split(" ")), key=len),
    "shortest": lambda s: min(_line(s).split(" "), key=len),
})

# H07 ------------------------------------------------------------------------
def _lcp(ws) -> str:
    p = ws[0]
    for w in ws[1:]:
        while not w.startswith(p):
            p = p[:-1]
    return p


def _lcp_gen(r) -> str:
    base = text(r, 0, 6, LOWER[:3])
    n = r.randint(2, 5)
    ws = [base + text(r, 0, 5, LOWER[:3]) for _ in range(n)]
    ws = [w or "a" for w in ws]
    return f"{n}\n" + "\n".join(ws)


register("H07", lambda s: _lcp(lines(s)[1:1 + int(lines(s)[0])]), _lcp_gen,
         ["2\na\nb", "3\nabc\nabc\nab", "2\nab\nabc", "3\nxyz\nxyw\nxa"], "multiline", {
    "first_two_only": lambda s: _lcp(lines(s)[1:3]),
    "last_two_only": lambda s: _lcp(lines(s)[int(lines(s)[0]) - 1:int(lines(s)[0]) + 1]),
})

# H08 ------------------------------------------------------------------------
register("H08", lambda s: " ".join(str(_line(s).count(str(d))) for d in range(10)),
         lambda r: text(r, 1, 300, "0123456789"), ["0", "9" * 256, "1" * 300, "0123456789" * 30], "int_out", {
    "one_to_ten": lambda s: " ".join(str(_line(s).count(str(d % 10))) for d in range(1, 11)),
    "presence_only": lambda s: " ".join("1" if str(d) in _line(s) else "0" for d in range(10)),
})

# H09 ------------------------------------------------------------------------
def _shift(s: str, mod=lambda a, b: a % b) -> str:
    k = int(lines(s)[0])
    return "".join(chr(mod(ord(c) - 97 + k, 26) + 97) for c in lines(s)[1])


register("H09", _shift, lambda r: f"{r.randint(-100, 100)}\n{text(r, 1, 20, LOWER)}",
         ["-1\na", "-27\nabc", "100\nxyz", "-100\nz", "52\nq", "25\nb"], "int_in neg_in multiline", {
    "c_remainder": lambda s: _shift(s, mod=lambda a, b: a - b * trunc_div(a, b)),
    "ignore_sign": lambda s: _shift(f"{abs(int(lines(s)[0]))}\n{lines(s)[1]}"),
})

# H10 ------------------------------------------------------------------------
register("H10", lambda s: "".join(c for i, c in enumerate(_line(s)) if i == 0 or _line(s)[i - 1] != c),
         lambda r: "".join(r.choice(LOWER[:4]) * r.randint(1, 4) for _ in range(r.randint(1, 10))),
         ["a", "aa", "abab", "aabbaa"], "str_in", {
    "global_dedupe": lambda s: "".join(dict.fromkeys(_line(s))),
    "pairs_only": lambda s: "".join(c for i, c in enumerate(_line(s)) if i % 2 == 0 or _line(s)[i - 1] != c),
})

# H11 ------------------------------------------------------------------------
register("H11", lambda s: "".join(c * int(k) for c, k in zip(_line(s)[::2], _line(s)[1::2])),
         lambda r: "".join(r.choice(LOWER) + str(r.randint(1, 9)) for _ in range(r.randint(1, 8))),
         ["a1", "a9b9", "a1a1"], "str_in", {
    "count_minus_one": lambda s: "".join(c * (int(k) - 1) for c, k in zip(_line(s)[::2], _line(s)[1::2])),
    "count_plus_one": lambda s: "".join(c * (int(k) + 1) for c, k in zip(_line(s)[::2], _line(s)[1::2])),
})

# H12 ------------------------------------------------------------------------
register("H12", lambda s: str(sum(map(ord, _line(s)))), lambda r: line_text(r, 1, 200),
         [" ", "~", "~~~", "a" * 200], "str_in int_out", {
    "letters_only": lambda s: str(sum(ord(c) for c in _line(s) if c.isalpha())),
    "minus_48": lambda s: str(sum(ord(c) - 48 for c in _line(s))),
})

# H13 ------------------------------------------------------------------------
def _poly(s: str, rev=False, drop_const=False) -> str:
    cs = ints(lines(s)[1])
    x = int(lines(s)[2])
    if rev:
        cs = cs[::-1]
    acc = 0
    for c in cs:
        acc = acc * x + c
    if drop_const:
        acc -= cs[-1]
    return str(acc)


register("H13", _poly, lambda r: (lambda n: f"{n}\n" + " ".join(str(r.randint(-10, 10)) for _ in range(n + 1))
                                  + f"\n{r.randint(-10, 10)}")(r.randint(0, 5)),
         ["0\n-7\n3", "1\n0 0\n5", "3\n1 2 3 4\n-2", "5\n1 0 0 0 0 1\n10", "2\n-1 -1 -1\n-10"],
         "int_in int_out neg_in multiline", {
    "lowest_degree_first": lambda s: _poly(s, rev=True),
    "drop_constant": lambda s: _poly(s, drop_const=True),
})

# H14 ------------------------------------------------------------------------
register("H14", lambda s: " ".join(str(d) for d in range(1, ints(s)[0] + 1) if ints(s)[0] % d == 0),
         lambda r: str(num(r, 1, 10000)), ["1", "2", "256", "9973", "10000", "720"], "int_in", {
    "proper_only": lambda s: " ".join(str(d) for d in range(1, ints(s)[0]) if ints(s)[0] % d == 0) or "1",
    "up_to_sqrt": lambda s: " ".join(str(d) for d in range(1, int(ints(s)[0] ** 0.5) + 1) if ints(s)[0] % d == 0),
})

# H15 ------------------------------------------------------------------------
register("H15", lambda s: str(_line(s).count("R") - _line(s).count("L")), lambda r: text(r, 1, 400, "LR"),
         ["L", "R" * 256, "L" * 300, "R" * 255 + "L"], "int_out", {
    "abs_position": lambda s: str(abs(_line(s).count("R") - _line(s).count("L"))),
    "no_negative": lambda s: str(max(0, _line(s).count("R") - _line(s).count("L"))),
})

# H16 ------------------------------------------------------------------------
def _runs(t: str):
    out, i = [], 0
    while i < len(t):
        j = i
        while j < len(t) and t[j] == t[i]:
            j += 1
        out.append(j - i)
        i = j
    return out


register("H16", lambda s: str(max(_runs(_line(s)))),
         lambda r: "".join(r.choice(LOWER[:3]) * r.choice([1, 2, 3, 9, 10, 12]) for _ in range(r.randint(1, 8))),
         ["a", "ab", "a" * 300, "abbb", "aaab"], "str_in int_out", {
    "first_run": lambda s: str(_runs(_line(s))[0]),
    "last_run_ignored": lambda s: str(max(_runs(_line(s))[:-1] or [1])),
})

# H17 ------------------------------------------------------------------------
def _mode(s: str, largest=False, first=False) -> str:
    vals = ints(lines(s)[1])
    cnt = {v: vals.count(v) for v in vals}
    top = max(cnt.values())
    tied = [v for v in vals if cnt[v] == top]
    if first:
        return str(tied[0])
    return str(max(tied) if largest else min(tied))


register("H17", _mode, lambda r: (lambda n: f"{n}\n" + " ".join(str(r.randint(-5, 5)) for _ in range(n)))(
    r.randint(1, 20)), ["2\n5 -5", "4\n3 3 -1 -1", "3\n9 8 7", "5\n2 1 1 2 0"], "int_in neg_in multiline", {
    "largest_on_tie": lambda s: _mode(s, largest=True),
    "first_seen_on_tie": lambda s: _mode(s, first=True),
})

# H18 ------------------------------------------------------------------------
register("H18", lambda s: "yes" if int(_line(s)) % 3 == 0 else "no",
         lambda r: str(r.randint(1, 9)) + text(r, 0, 59, "0123456789"),
         ["0", "3", "10", "111111111111111111111111111111", "1" * 59 + "2"], "", {
    "last_digit": lambda s: "yes" if int(_line(s)[-1]) % 3 == 0 else "no",
    "last_9_digits": lambda s: "yes" if int(_line(s)[-9:]) % 3 == 0 else "no",
})

# H19 ------------------------------------------------------------------------
def _pm0(t: str, reset=True) -> int:
    x = 0
    for c in t:
        x = x + 1 if c == "+" else x - 1 if c == "-" else (0 if reset else x)
    return x


register("H19", lambda s: str(_pm0(_line(s))), lambda r: text(r, 1, 400, "++--0" if r.random() < .5 else "+++-0"),
         ["0", "-", "-0-", "+" * 256, "-" * 300, "+" * 300 + "0"], "int_out", {
    "zero_ignored": lambda s: str(_pm0(_line(s), reset=False)),
    "abs_result": lambda s: str(abs(_pm0(_line(s)))),
})

# H20 ------------------------------------------------------------------------
def _strs_gen(r) -> str:
    n = r.randint(1, 8)
    alpha = LOWER if r.random() < 0.6 else "abcABC"
    return f"{n}\n" + "\n".join(text(r, 1, 6, alpha) for _ in range(n))


register("H20", lambda s: " ".join(sorted(lines(s)[1:1 + int(lines(s)[0])])), _strs_gen,
         ["2\nb\nB", "3\nab\na\nabc", "2\nZ\na", "3\nbb\nb\nba"], "multiline", {
    "case_insensitive": lambda s: " ".join(sorted(lines(s)[1:1 + int(lines(s)[0])], key=str.lower)),
    "by_length": lambda s: " ".join(sorted(lines(s)[1:1 + int(lines(s)[0])], key=lambda w: (len(w), w))),
})
