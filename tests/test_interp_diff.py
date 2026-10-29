"""esoforge's interpreters (official dialect) must agree with the paper's interpreters."""
import pytest

from esoforge.difftest import dialect_gaps, esoforge_outcome, fuzz, upstream_outcome
from esoforge.esoc.wsasm import assemble
from esoforge.interp import run


@pytest.mark.parametrize("language", ["brainfuck", "whitespace", "befunge98"])
def test_fuzz_agrees_with_official(language):
    rep = fuzz(language, cases=1500, seed=7)
    assert rep.mismatches == [], rep.mismatches[:3]


def test_bf_step_limit_matches_exactly():
    prog = "+" * 10 + "[>++++++++++<-]>[-]" + "+" * 50
    for limit in range(1, 400, 7):
        a = esoforge_outcome("brainfuck", prog, "", limit)
        b = upstream_outcome("brainfuck", prog, "", limit)
        assert a.key() == b.key(), limit


def test_bf_negative_pointer_error():
    assert run("bf", "<").error.startswith("RuntimeError")
    assert run("bf", "+[<+>-]").error.startswith("RuntimeError")


def test_bf_unbalanced():
    assert run("bf", "[").error.startswith("SyntaxError")
    assert run("bf", "]").error.startswith("SyntaxError")


def test_ws_division_quirk_official_vs_spec():
    big = 2 ** 60 + 3
    prog = assemble([("push", big), ("push", 10), ("div", None), ("out_num", None), ("end", None)])
    assert run("ws", prog, dialect="spec").output == str(big // 10)
    assert run("ws", prog, dialect="official").output == str(int(big / 10))
    assert run("ws", prog, dialect="official").output != str(big // 10)  # float precision loss
    neg = assemble([("push", -7), ("push", 2), ("div", None), ("out_num", None), ("end", None)])
    assert run("ws", neg, dialect="official").output == "-3"   # truncates
    assert run("ws", neg, dialect="spec").output == "-4"       # floors (reference Haskell div)


def test_b98_byte_cells_official_vs_spec():
    prog = '"d"2*00p00g.@'   # store 200 then 400? '"d"' pushes 100, *2 = 200
    prog = "a8*5*00p00g.@"   # 400 -> official keeps 400 % 256 = 144
    assert run("b98", prog, dialect="official").output == "144 "
    assert run("b98", prog, dialect="spec").output == "400 "


def test_b98_division_by_zero():
    assert run("b98", "10/.@", dialect="official").error.startswith("DivisionByZero")
    assert run("b98", "10/.@", dialect="spec").output == "0 "


def test_dialect_gaps_exist_only_where_documented():
    gaps = dialect_gaps("brainfuck", cases=300, seed=3)
    assert gaps == []
