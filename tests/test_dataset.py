import pytest

from esoforge.dataset import DatasetIntegrityError, get_problem, load_problems, problem_ids


def test_eighty_problems_in_benchmark_order():
    ids = problem_ids()
    assert len(ids) == 80
    assert ids[:2] == ["E01", "E02"] and ids[20] == "M01" and ids[40] == "H01" and ids[-1] == "X20"


def test_six_tests_each_and_tiers():
    for p in load_problems().values():
        assert len(p.tests) == 6
        assert p.difficulty == {"E": "easy", "M": "medium", "H": "hard", "X": "extra_hard"}[p.id[0]]


def test_get_problem_case_insensitive():
    assert get_problem("e04").title == "Sum Two Integers"
    with pytest.raises(KeyError):
        get_problem("Z99")


def test_checksum_is_enforced(tmp_path, monkeypatch):
    import esoforge.dataset as ds
    bad = tmp_path / "x.jsonl"
    bad.write_text(ds.DATA_PATH.read_text() + "\n")
    monkeypatch.setattr(ds, "DATA_PATH", bad)
    ds.load_problems.cache_clear()
    try:
        with pytest.raises(DatasetIntegrityError):
            ds.load_problems()
    finally:
        monkeypatch.undo()
        ds.load_problems.cache_clear()
