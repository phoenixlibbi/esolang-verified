"""esoc: IR semantics, backends, and the 80 reference programs."""
import random

import pytest

from esoverified.dataset import load_problems, problem_ids
from esoverified.esoc import compile_problem, compile_program
from esoverified.esoc.b98 import push_num
from esoverified.esoc.bf import Emitter, ge_const
from esoverified.esoc.fuzz import random_input, random_program
from esoverified.esoc.ir import Builder, IRError, interpret
from esoverified.esoc.lib import Input, fdiv, fmod, tdiv, tmod
from esoverified.esoc.programs import available, build
from esoverified.freshtests import fresh_suite
from esoverified.interp import run

PIDS = problem_ids()


def test_every_problem_has_a_program():
    assert available() == PIDS


@pytest.mark.parametrize("pid", PIDS)
def test_ir_program_matches_reference(pid):
    prog = build(pid)
    for inp, exp in list(load_problems()[pid].tests) + fresh_suite(pid, 0, 30):
        r = interpret(prog, inp)
        assert r.output == exp, (inp, exp, r.output)
        assert r.max_abs <= prog.max_value and r.max_inter <= prog.max_inter


@pytest.mark.parametrize("pid", PIDS)
def test_whitespace_oracle_passes_official_tests(pid):
    src = compile_problem(pid, "whitespace")
    for inp, exp in load_problems()[pid].tests:
        assert run("whitespace", src, inp).output == exp


@pytest.mark.parametrize("pid", ["E01", "E04", "E19", "M03", "M08", "H02", "H09", "X04", "X14", "X17"])
def test_befunge_oracle_passes_official_tests(pid):
    src = compile_problem(pid, "befunge98")
    for inp, exp in load_problems()[pid].tests:
        r = run("befunge98", src, inp)
        assert r.output == exp, (inp, r.error)
        assert run("befunge98", src, inp, dialect="spec").output == exp   # no reliance on quirks


@pytest.mark.slow
@pytest.mark.parametrize("pid", PIDS)
def test_befunge_oracle_passes_fresh_tests(pid):
    src = compile_problem(pid, "befunge98")
    for inp, exp in list(load_problems()[pid].tests) + fresh_suite(pid, 0, 30):
        assert run("befunge98", src, inp).output == exp


@pytest.mark.parametrize("pid", ["E01", "E02", "E03", "E15", "H10", "E17"])
def test_brainfuck_oracle_passes_official_tests(pid):
    src = compile_problem(pid, "brainfuck")
    for inp, exp in load_problems()[pid].tests:
        r = run("brainfuck", src, inp)
        assert r.output == exp, (inp, r.error)


def test_signed_division_macros():
    P = Builder("t")
    I = Input(P)
    a, b = P.var("a"), P.var("b")
    I.read_int(a)
    I.read_int(b)
    for f in (tdiv, tmod, fdiv, fmod):
        P.print_int(f(a, b))
        P.print_char(32)
    prog = P.build()
    for x in range(-9, 10):
        for y in (-4, -3, -1, 1, 2, 5):
            q = abs(x) // abs(y) * (1 if (x >= 0) == (y >= 0) else -1)
            want = f"{q} {x - y * q} {x // y} {x % y} "
            assert interpret(prog, f"{x} {y}").output == want


def test_udiv_rejects_negative_operands():
    from esoverified.esoc.ir import udiv
    P = Builder("t")
    a = P.var("a", -5)
    P.print_int(udiv(a, 2))
    with pytest.raises(IRError):
        interpret(P.build())


def test_builder_errors():
    P = Builder("t")
    P.var("x")
    with pytest.raises(ValueError):
        P.var("x")
    with pytest.raises(SyntaxError):
        with P.else_():
            pass


@pytest.mark.parametrize("n", list(range(-300, 300, 7)) + [59, 2 ** 31, 2 ** 47, 10 ** 12])
def test_b98_push_num(n):
    assert run("b98", push_num(n) + ".@").output == f"{n} "


@pytest.mark.parametrize("c", [0, 1, 9, 10, 48, 97, 123, 255])
def test_bf_ge_const_is_exact(c):
    for v in range(0, 256, 3):
        e = Emitter(trick=10)
        e.add(0, v)
        ge_const(e, 0, c, 1, [2, 3, 4, 5, 6])
        e.at(1)
        e.raw(".")
        assert run("bf", e.text()).output == chr(int(v >= c))


@pytest.mark.parametrize("lang", ["whitespace", "befunge98"])
def test_random_programs_agree_with_ir(lang):
    rng = random.Random(11)
    checked = 0
    while checked < 12:
        prog = random_program(rng)
        inp = random_input(rng)
        try:
            ref = interpret(prog, inp)
        except IRError:
            continue
        assert run(lang, compile_program(prog, lang), inp).output == ref.output
        checked += 1


@pytest.mark.slow
def test_random_programs_agree_with_ir_brainfuck():
    rng = random.Random(12)
    checked = 0
    while checked < 6:
        prog = random_program(rng, n_stmts=6, depth=1)
        inp = random_input(rng)
        try:
            ref = interpret(prog, inp)
        except IRError:
            continue
        assert run("bf", compile_program(prog, "bf"), inp).output == ref.output
        checked += 1
