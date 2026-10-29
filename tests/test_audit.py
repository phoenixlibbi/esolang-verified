from esoverified.audit import audit_problem, summarize
from esoverified.mutants import Mutant
from esoverified.problems import get_spec


def _by_name(audit, name):
    return next(m for m in audit.mutants if m.name == name)


def test_floor_division_passes_official_tests_but_not_fresh():
    a = audit_problem("E19")
    m = _by_name(a, "floor_division")
    assert not m.equivalent and not m.killed_official and m.killed_fresh
    assert m.witness is not None and m.witness[1] != m.witness[2]


def test_equivalent_mutant_is_excluded():
    ref = get_spec("E04").solve
    a = audit_problem("E04", mutants=[Mutant("same", "specific", lambda s: ref(s))])
    assert a.mutants[0].equivalent and a.valid == []
    assert a.score() is None


def test_crashing_mutant_counts_as_killed():
    def boom(s):
        raise ValueError
    a = audit_problem("E04", mutants=[Mutant("boom", "specific", boom)])
    m = a.mutants[0]
    assert not m.equivalent and m.killed_official and m.witness[2] == "<crash>"


def test_whitespace_only_difference_is_policy_only():
    ref = get_spec("E02").solve
    a = audit_problem("E02", mutants=[Mutant("trim", "whitespace", lambda s: ref(s).strip())])
    m = a.mutants[0]
    assert m.equivalent and m.policy_only   # invisible to the official strip() comparison


def test_summary_counts_are_consistent():
    audits = [audit_problem(p) for p in ("E04", "E19", "X04")]
    s = summarize(audits)
    assert s.mutants_valid + s.equivalent == s.mutants_total
    assert 0 <= s.survivors_fresh <= s.survivors_official <= s.mutants_valid
    assert sum(r["valid"] for r in s.by_family.values()) == s.mutants_valid
