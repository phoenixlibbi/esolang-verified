import random

import pytest

from esoforge.dataset import load_problems
from esoforge.freshtests import GoldSanityError, check_reference, fresh_suite, input_pool
from esoforge.mutants import mutants_for
from esoforge.problems import all_specs

PIDS = list(load_problems())


def test_every_problem_has_a_spec():
    assert list(all_specs()) == PIDS


@pytest.mark.parametrize("pid", PIDS)
def test_reference_reproduces_official_tests_exactly(pid):
    check_reference(pid)


@pytest.mark.parametrize("pid", PIDS)
def test_generators_and_edges_are_valid_inputs(pid):
    spec = all_specs()[pid]
    rng = random.Random(5)
    for x in [spec.gen(rng) for _ in range(200)] + list(spec.edges):
        out = spec.solve(x)
        assert isinstance(out, str)
        assert "\n" not in out


def test_pool_is_deterministic_and_seed_dependent():
    assert input_pool("E04", 1, 20) == input_pool("E04", 1, 20)
    assert input_pool("E04", 1, 20) != input_pool("E04", 2, 20)


def test_fresh_suite_contains_edges_and_reference_outputs():
    suite = fresh_suite("E19", seed=3, n_random=10)
    assert ("-1 0", "0") in suite      # truncation toward zero, as the statement says
    assert len(suite) >= 10


def test_gold_sanity_rejects_a_broken_reference(monkeypatch):
    import esoforge.problems as P
    spec = P.get_spec("E04")
    broken = P.ProblemSpec(spec.pid, lambda s: "0", spec.gen, spec.edges, spec.tags, spec.mutants)
    monkeypatch.setitem(P.REGISTRY, "E04", broken)
    with pytest.raises(GoldSanityError):
        check_reference("E04")


def test_mutant_names_unique_per_problem():
    for pid in PIDS:
        names = [m.name for m in mutants_for(pid)]
        assert len(names) == len(set(names)), pid
