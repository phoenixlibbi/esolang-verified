"""X01-X20: combined control flow and data manipulation."""

from __future__ import annotations

from .util import LOWER, ints, lines, num, text, trunc_div
from . import register


def _line(s: str) -> str:
    return lines(s)[0]


def _n_list(s: str):
    return ints(lines(s)[1])


def _n_then_list(r, n_lo, n_hi, lo, hi) -> str:
    n = r.randint(n_lo, n_hi)
    return f"{n}\n" + " ".join(str(num(r, lo, hi)) for _ in range(n))


# X01 ------------------------------------------------------------------------
def _factor(n: int, upto=None):
    out, p = [], 2
    while p * p <= n and (upto is None or p <= upto):
        while n % p == 0:
            out.append(p)
            n //= p
        p += 1
    if n > 1 and (upto is None):
        out.append(n)
    return out


register("X01", lambda s: " ".join(map(str, _factor(ints(s)[0]))), lambda r: str(num(r, 2, 10 ** 6)),
         ["2", "4", "97", "256", "999983", "1000000", "510510"], "int_in", {
    "distinct_primes": lambda s: " ".join(map(str, sorted(set(_factor(ints(s)[0]))))),
    "forgets_last_prime": lambda s: " ".join(map(str, _factor(ints(s)[0], upto=10 ** 9))) or str(ints(s)[0]),
})

# X02 ------------------------------------------------------------------------
def _lis(a, strict=True) -> int:
    best = [1] * len(a)
    for i in range(len(a)):
        for j in range(i):
            if (a[j] < a[i]) if strict else (a[j] <= a[i]):
                best[i] = max(best[i], best[j] + 1)
    return max(best)


def _longest_run_inc(a) -> int:
    best = cur = 1
    for i in range(1, len(a)):
        cur = cur + 1 if a[i] > a[i - 1] else 1
        best = max(best, cur)
    return best


register("X02", lambda s: str(_lis(_n_list(s))), lambda r: _n_then_list(r, 1, 15, -50, 50),
         ["1\n5", "3\n2 2 2", "4\n1 2 2 3", "5\n-5 -4 -3 -2 -1", "6\n1 5 2 6 3 7"], "int_in neg_in multiline", {
    "non_strict": lambda s: str(_lis(_n_list(s), strict=False)),
    "contiguous_only": lambda s: str(_longest_run_inc(_n_list(s))),
})

# X03 ------------------------------------------------------------------------
def _mat(s: str, transpose_b=False) -> str:
    ls = lines(s)
    m, n, p = ints(ls[0])
    a = [ints(ls[1 + i]) for i in range(m)]
    b = [ints(ls[1 + m + k]) for k in range(n)]
    i, j = ints(ls[1 + m + n])
    if transpose_b:  # uses B[j][k] instead of B[k][j] (only valid when square enough)
        return str(sum(a[i][k] * b[j % n][k % p] for k in range(n)))
    return str(sum(a[i][k] * b[k][j] for k in range(n)))


def _mat_gen(r) -> str:
    m, n, p = r.randint(1, 4), r.randint(1, 4), r.randint(1, 4)
    rows = [" ".join(str(r.randint(-9, 9)) for _ in range(n)) for _ in range(m)]
    rows += [" ".join(str(r.randint(-9, 9)) for _ in range(p)) for _ in range(n)]
    return f"{m} {n} {p}\n" + "\n".join(rows) + f"\n{r.randrange(m)} {r.randrange(p)}"


register("X03", _mat, _mat_gen, ["1 3 1\n1 2 3\n4\n5\n6\n0 0", "2 2 2\n1 2\n3 4\n5 6\n7 8\n1 0",
                                 "1 1 3\n-2\n1 2 3\n0 2"], "int_in int_out neg_in multiline", {
    "b_transposed": lambda s: _mat(s, transpose_b=True),
    "first_term_only": lambda s: _mat_first_term(s),
})


def _mat_first_term(s: str) -> str:
    ls = lines(s)
    m, n, _ = ints(ls[0])
    i, j = ints(ls[1 + m + n])
    return str(ints(ls[1 + i])[0] * ints(ls[1 + m])[j])

# X04 ------------------------------------------------------------------------
def _rpn(e: str, div=trunc_div) -> str:
    st = []
    for tok in e.split():
        if tok in "+-*/":
            b, a = st.pop(), st.pop()
            st.append(a + b if tok == "+" else a - b if tok == "-" else a * b if tok == "*" else div(a, b))
        else:
            st.append(int(tok))
    return str(st[-1])


def _rpn_gen(r) -> str:
    while True:
        toks, depth = [], 0
        for _ in range(r.randint(1, 12)):
            if depth >= 2 and r.random() < 0.5:
                toks.append(r.choice("+-*/"))
                depth -= 1
            else:
                toks.append(str(r.randint(0, 9)))
                depth += 1
        toks += [r.choice("+-*/") for _ in range(depth - 1)]
        try:
            _rpn(" ".join(toks))
            return " ".join(toks)
        except ZeroDivisionError:
            continue


register("X04", lambda s: _rpn(_line(s)), _rpn_gen,
         ["7", "1 2 -", "3 7 - 2 /", "0 9 - 4 /", "9 9 * 9 * 9 *", "1 2 3 4 5 + + + +"], "int_out", {
    "floor_division": lambda s: _rpn(_line(s), div=lambda a, b: a // b),
    "minus_operands_swapped": lambda s: str(_rpn_swapped(_line(s))),
})


def _rpn_swapped(e: str) -> int:
    st = []
    for tok in e.split():
        if tok in "+-*/":
            b, a = st.pop(), st.pop()
            st.append(a + b if tok == "+" else b - a if tok == "-" else a * b if tok == "*" else trunc_div(a, b))
        else:
            st.append(int(tok))
    return st[-1]


# X05 ------------------------------------------------------------------------
def _merge_gen(r) -> str:
    a = sorted(num(r, -999, 999) for _ in range(r.randint(1, 10)))
    b = sorted(num(r, -999, 999) for _ in range(r.randint(1, 10)))
    return " ".join(map(str, a)) + "\n" + " ".join(map(str, b))


register("X05", lambda s: " ".join(map(str, sorted(ints(lines(s)[0]) + ints(lines(s)[1])))), _merge_gen,
         ["5\n1", "-1\n-2", "1 1\n1", "-10 -5 0\n-7", "255\n256"], "int_in neg_in multiline", {
    "concat_no_merge": lambda s: " ".join(lines(s)[0].split() + lines(s)[1].split()),
    "string_sort": lambda s: " ".join(sorted(lines(s)[0].split() + lines(s)[1].split())),
})

# X06 ------------------------------------------------------------------------
register("X06", lambda s: str(pow(*ints(s))), lambda r: f"{num(r, 0, 1000)} {num(r, 0, 10 ** 9)} {num(r, 1, 10 ** 6)}",
         ["0 0 7", "5 0 1", "7 3 1", "2 100 1000000", "999 999999999 999983", "1000 1 7"], "int_in int_out", {
    "e0_forgets_mod": lambda s: "1" if ints(s)[1] == 0 else str(pow(*ints(s))),
    "u32_overflow": lambda s: (lambda b, e, m: str(_powmod_u32(b, e, m)))(*ints(s)),
})


def _powmod_u32(b: int, e: int, m: int) -> int:
    res, b = 1, b % m
    while e:
        if e & 1:
            res = (res * b) % 2 ** 32 % m
        b = (b * b) % 2 ** 32 % m
        e >>= 1
    return res % m


# X07 ------------------------------------------------------------------------
def _lps(t: str, odd_only=False) -> int:
    best = 0
    for c in range(len(t)):
        for lo, hi in ((c, c), (c, c + 1)):
            if odd_only and hi != lo:
                continue
            while lo >= 0 and hi < len(t) and t[lo] == t[hi]:
                lo -= 1
                hi += 1
            best = max(best, hi - lo - 1)
    return best


register("X07", lambda s: str(_lps(_line(s))), lambda r: text(r, 1, 30, "aab" if r.random() < .5 else "abc"),
         ["a", "aa", "ab", "abba", "aaaa", "abcba"], "str_in int_out", {
    "odd_length_only": lambda s: str(_lps(_line(s), odd_only=True)),
    "whole_or_one": lambda s: str(len(_line(s)) if _line(s) == _line(s)[::-1] else 1),
})

# X08 ------------------------------------------------------------------------
register("X08", lambda s: str(sum(bin(v).count("1") for v in range(ints(s)[0], ints(s)[1] + 1))),
         lambda r: (lambda lo: f"{lo} {lo + r.randint(0, 1000)}")(num(r, 0, 10000)),
         ["0 0", "7 7", "255 256", "0 1023", "10000 11000"], "int_in int_out", {
    "exclusive_r": lambda s: str(sum(bin(v).count("1") for v in range(ints(s)[0], ints(s)[1]))),
    "endpoints_only": lambda s: str(bin(ints(s)[0]).count("1") + bin(ints(s)[1]).count("1")),
})

# X09 ------------------------------------------------------------------------
def _depth(t: str, clamp=True) -> int:
    d = best = 0
    for c in t:
        d += 1 if c == "(" else -1
        if clamp:
            d = max(d, 0)
        best = max(best, d)
    return best


# The official test ')))((' -> '2' fixes the semantics: depth never goes below zero.
register("X09", lambda s: str(_depth(_line(s), clamp=True)), lambda r: text(r, 0, 40, "(()" if r.random() < .5 else "())"),
         ["", ")", ")(", "))((", "())(((", "(" * 300, ")))((((((", ")()("], "str_in int_out", {
    "goes_negative": lambda s: str(_depth(_line(s), clamp=False)),
    "count_open": lambda s: str(_line(s).count("(")),
})

# X10 ------------------------------------------------------------------------
def _rot_gen(r) -> str:
    a = text(r, 1, 12, "abc")
    k = r.randrange(len(a))
    b = a[k:] + a[:k]
    if r.random() < 0.5:
        bl = list(b)
        bl[r.randrange(len(bl))] = r.choice("abc")
        b = "".join(bl)
    return f"{a}\n{b}"


register("X10", lambda s: "yes" if len(lines(s)[0]) == len(lines(s)[1]) and lines(s)[1] in lines(s)[0] * 2
         else "no", _rot_gen, ["a\na", "ab\nba", "aab\naba", "abc\nacb", "aaab\naaba", "abab\nbaba"],
         "str_in multiline", {
    "same_letters": lambda s: "yes" if sorted(lines(s)[0]) == sorted(lines(s)[1]) else "no",
    "single_rotation_only": lambda s: "yes" if lines(s)[1] in (lines(s)[0], lines(s)[0][1:] + lines(s)[0][:1],
                                                                lines(s)[0][-1:] + lines(s)[0][:-1]) else "no",
})

# X11 ------------------------------------------------------------------------
def _inv(a, strict=True) -> int:
    return sum(1 for i in range(len(a)) for j in range(i + 1, len(a)) if (a[i] > a[j] if strict else a[i] >= a[j]))


register("X11", lambda s: str(_inv(_n_list(s))), lambda r: _n_then_list(r, 1, 30, -20, 20),
         ["1\n0", "2\n1 1", "3\n-1 -2 -3", "30\n" + " ".join(str(30 - i) for i in range(30))],
         "int_in int_out neg_in multiline", {
    "counts_equal_pairs": lambda s: str(_inv(_n_list(s), strict=False)),
    "adjacent_only": lambda s: str(sum(1 for x, y in zip(_n_list(s), _n_list(s)[1:]) if x > y)),
})

# X12 ------------------------------------------------------------------------
def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


register("X12", lambda s: str(ints(s)[0] * ints(s)[1] // _gcd(*ints(s))),
         lambda r: f"{num(r, 1, 10000)} {num(r, 1, 10000)}", ["1 1", "16 24", "9999 10000", "255 256", "17 17"],
         "int_in int_out", {
    "product": lambda s: str(ints(s)[0] * ints(s)[1]),
    "max_if_divides_else_product": lambda s: (lambda a, b: str(max(a, b) if max(a, b) % min(a, b) == 0 else a * b))(
        *ints(s)),
})

# X13 ------------------------------------------------------------------------
def _valid(t: str, typed=True) -> bool:
    pairs = {")": "(", "]": "[", "}": "{"}
    st = []
    for c in t:
        if c in "([{":
            st.append(c)
        else:
            if not st or (typed and st[-1] != pairs[c]):
                return False
            st.pop()
    return not st


def _brackets_gen(r) -> str:
    if r.random() < 0.5:
        out, st = [], []
        for _ in range(r.randint(1, 12)):
            if st and r.random() < 0.5:
                out.append({"(": ")", "[": "]", "{": "}"}[st.pop()])
            else:
                c = r.choice("([{")
                st.append(c)
                out.append(c)
        out += [{"(": ")", "[": "]", "{": "}"}[c] for c in reversed(st)]
        return "".join(out)
    return text(r, 1, 16, "()[]{}")


register("X13", lambda s: "yes" if _valid(_line(s)) else "no", _brackets_gen,
         ["(]", "([)]", "(((", "}{", "[](){}", "{[()()]}"], "str_in", {
    "ignores_types": lambda s: "yes" if _valid(_line(s), typed=False) else "no",
    "per_type_counts": lambda s: "yes" if all(_line(s).count(a) == _line(s).count(b)
                                              for a, b in ("()", "[]", "{}")) else "no",
})

# X14 ------------------------------------------------------------------------
def _nge(a, ge=False, nxt=False):
    out = []
    for i, v in enumerate(a):
        cands = a[i + 1:i + 2] if nxt else a[i + 1:]
        out.append(next((w for w in cands if (w >= v if ge else w > v)), -1))
    return " ".join(map(str, out))


register("X14", lambda s: _nge(_n_list(s)), lambda r: _n_then_list(r, 1, 15, -9, 30),
         ["1\n5", "3\n2 2 3", "4\n-5 -6 -1 -1", "3\n1 1 1"], "int_in neg_in multiline", {
    "greater_or_equal": lambda s: _nge(_n_list(s), ge=True),
    "immediate_right_only": lambda s: _nge(_n_list(s), nxt=True),
})

# X15 ------------------------------------------------------------------------
def _spiral(s: str) -> str:
    ls = lines(s)
    rows, cols = ints(ls[0])
    m = [ints(ls[1 + i]) for i in range(rows)]
    out = []
    top, bot, left, right = 0, rows - 1, 0, cols - 1
    while top <= bot and left <= right:
        out += [m[top][j] for j in range(left, right + 1)]
        out += [m[i][right] for i in range(top + 1, bot + 1)]
        if top < bot:
            out += [m[bot][j] for j in range(right - 1, left - 1, -1)]
        if left < right:
            out += [m[i][left] for i in range(bot - 1, top, -1)]
        top, bot, left, right = top + 1, bot - 1, left + 1, right - 1
    return " ".join(map(str, out))


def _spiral_buggy(s: str) -> str:
    # forgets the "single remaining row/column" guards: duplicates elements
    ls = lines(s)
    rows, cols = ints(ls[0])
    m = [ints(ls[1 + i]) for i in range(rows)]
    out = []
    top, bot, left, right = 0, rows - 1, 0, cols - 1
    while top <= bot and left <= right:
        out += [m[top][j] for j in range(left, right + 1)]
        out += [m[i][right] for i in range(top + 1, bot + 1)]
        out += [m[bot][j] for j in range(right - 1, left - 1, -1)]
        out += [m[i][left] for i in range(bot - 1, top, -1)]
        top, bot, left, right = top + 1, bot - 1, left + 1, right - 1
    return " ".join(map(str, out))


def _spiral_gen(r) -> str:
    rows, cols = r.randint(1, 5), r.randint(1, 5)
    k = iter(range(1, rows * cols + 1))
    return f"{rows} {cols}\n" + "\n".join(" ".join(str(next(k)) for _ in range(cols)) for _ in range(rows))


register("X15", _spiral, _spiral_gen, ["1 1\n7", "3 1\n1\n2\n3", "1 3\n1 2 3", "3 4\n1 2 3 4\n5 6 7 8\n9 10 11 12",
                                       "4 3\n1 2 3\n4 5 6\n7 8 9\n10 11 12"], "multiline", {
    "missing_guards": _spiral_buggy,
    "row_major": lambda s: " ".join(" ".join(ls) for ls in [l.split() for l in lines(s)[1:]]),
})

# X16 ------------------------------------------------------------------------
register("X16", lambda s: str(bin(ints(s)[0] ^ ints(s)[1]).count("1")),
         lambda r: f"{num(r, 0, 10 ** 9)} {num(r, 0, 10 ** 9)}", ["0 256", "256 0", "1023 0", "1000000000 0", "5 5"],
         "int_in int_out", {
    "low_byte_only": lambda s: str(bin((ints(s)[0] ^ ints(s)[1]) & 255).count("1")),
    "popcount_difference": lambda s: str(abs(bin(ints(s)[0]).count("1") - bin(ints(s)[1]).count("1"))),
})

# X17 ------------------------------------------------------------------------
_ROM = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


def _to_roman(n: int) -> str:
    out = []
    for v, sym in _ROM:
        while n >= v:
            out.append(sym)
            n -= v
    return "".join(out)


def _from_roman(t: str, subtractive=True) -> int:
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    tot = 0
    for i, c in enumerate(t):
        v = vals[c]
        if subtractive and i + 1 < len(t) and vals[t[i + 1]] > v:
            tot -= v
        else:
            tot += v
    return tot


register("X17", lambda s: str(_from_roman(_line(s))), lambda r: _to_roman(r.randint(1, 3999)),
         ["I", "MMMCMXCIX", "CDXLIV", "XC", "MCD", "CCLVI"], "str_in int_out", {
    "no_subtractive": lambda s: str(_from_roman(_line(s), subtractive=False)),
    # handles IV and IX but not XL, XC, CD, CM
    "only_IV_IX": lambda s: str(_from_roman(_line(s).replace("IV", "IIII").replace("IX", "VIIII"),
                                            subtractive=False)),
})

# X18 ------------------------------------------------------------------------
register("X18", lambda s: _to_roman(ints(s)[0]), lambda r: str(r.randint(1, 3999)),
         ["1", "4", "3999", "444", "999", "1990", "256"], "int_in", {
    "additive_only": lambda s: "".join(sym * (n // v) for v, sym, n in
                                        _additive_parts(ints(s)[0])),
    "byte_cell_number": lambda s: _to_roman(ints(s)[0] % 256 or 256),
})


def _additive_parts(n: int):
    parts = []
    for v, sym in [(1000, "M"), (500, "D"), (100, "C"), (50, "L"), (10, "X"), (5, "V"), (1, "I")]:
        parts.append((v, sym, n))
        n %= v
    return parts


# X19 ------------------------------------------------------------------------
def _perm_gen(r) -> str:
    n = r.randint(1, 15)
    a = list(range(1, n + 1))
    r.shuffle(a)
    if r.random() < 0.5:
        a[r.randrange(n)] = r.choice([0, n + 1, r.randint(1, n), -1])
    return f"{n}\n" + " ".join(map(str, a))


register("X19", lambda s: "yes" if sorted(_n_list(s)) == list(range(1, int(lines(s)[0]) + 1)) else "no", _perm_gen,
         ["1\n0", "2\n2 1", "3\n0 1 2", "3\n1 2 4", "2\n1 1"], "int_in multiline", {
    "range_check_only": lambda s: "yes" if all(1 <= v <= int(lines(s)[0]) for v in _n_list(s)) else "no",
    "sum_check_only": lambda s: "yes" if sum(_n_list(s)) == int(lines(s)[0]) * (int(lines(s)[0]) + 1) // 2 else "no",
})

# X20 ------------------------------------------------------------------------
def _jos(n: int, k: int, start_next: bool = True) -> int:
    people = list(range(1, n + 1))
    i = 0
    while len(people) > 1:
        i = (i + k - 1) % len(people)
        people.pop(i)
        if not start_next:
            i = 0
    return people[0]


register("X20", lambda s: str(_jos(*ints(s))), lambda r: (lambda n: f"{n} {r.randint(1, 2 * n)}")(r.randint(1, 60)),
         ["1 5", "2 1", "2 2", "3 7", "60 60", "41 3", "51 100", "60 120"], "int_in int_out", {
    "restart_from_first": lambda s: str(_jos(*ints(s), start_next=False)),
    "k_minus_one": lambda s: (lambda n, k: str(_jos(n, max(1, k - 1))))(*ints(s)),
})
