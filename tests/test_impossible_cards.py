import pytest

from esoverified.cards import card_for
from esoverified.dataset import problem_ids
from esoverified.impossible import contradict, impossible_tests
from esoverified.problems import get_spec


@pytest.mark.parametrize("pid", problem_ids())
@pytest.mark.parametrize("mode", ["oneoff", "conflict"])
def test_reference_cannot_pass_impossible_variant(pid, mode):
    tests = impossible_tests(pid, seed=3, mode=mode)
    ref = get_spec(pid).solve
    assert sum(ref(i) != o for i, o in tests) == 1


def test_contradict_changes_output():
    for e in ["yes", "no", "12", "-3", "a b", "", "1 2 3"]:
        assert contradict(e) != e


@pytest.mark.parametrize("lang", ["brainfuck", "befunge98", "whitespace"])
def test_cards(lang):
    card = card_for(lang)
    assert card.startswith("## ") and "Language Reference" in card.splitlines()[0]
