import subprocess
import sys

import pytest

from esoverified.esoc.bfgen import print_text
from esoverified.harness import GraderServer, HarnessConfig, Session, request, write_client


def _session(**kw):
    return Session(HarnessConfig(language="brainfuck", problems=["E01", "E02"], **kw))


def test_forward_protocol_and_cap():
    s = _session()
    assert s.fetch()["id"] == "E01"
    assert not s.fetch()["ok"]                      # cannot move on with submissions left
    for k in range(3):
        r = s.submit("E01", "")
        assert r["ok"] and not r["solved"] and r["submissions_left"] == 2 - k
    assert not s.submit("E01", "")["ok"]            # cap enforced
    assert s.fetch()["id"] == "E02"
    assert s.export()["problems"]["E01"]["status"] == "failed"
    assert not s.submit("E01", print_text("Hello World!"))["ok"]   # no revisits


def test_honest_solution_is_solved_with_fresh_tests():
    s = _session(tests="fresh", fresh_seed=11)
    s.fetch()
    r = s.submit("E01", print_text("Hello World!"))
    assert r["solved"] and r["passed"] == r["total"]
    assert "per_test" not in r                       # aggregate feedback by default


def test_per_test_feedback_is_opt_in():
    s = _session(feedback="per_test")
    s.fetch()
    assert len(s.submit("E01", "")["per_test"]) == 6


def test_run_budget():
    s = _session(run_budget=2)
    s.fetch()
    assert s.run("+.", "")["ok"] and s.run("+.", "")["ok"]
    assert not s.run("+.", "")["ok"]


def test_policies():
    padded = print_text("Hello World!  \n")
    for policy, solved in (("official", True), ("newline", False), ("exact", False)):
        s = _session(policy=policy)
        s.fetch()
        assert s.submit("E01", padded)["solved"] is solved, policy
    s = _session(policy="newline")
    s.fetch()
    assert s.submit("E01", print_text("Hello World!\n"))["solved"]


def test_skip_and_bad_requests():
    s = _session()
    s.fetch()
    assert s.skip()["ok"] and s.fetch()["id"] == "E02"
    assert not s.handle({"cmd": "nope"})["ok"]
    assert not s.handle({"cmd": "submit", "id": "E99", "code": ""})["ok"]


def test_config_validation():
    with pytest.raises(ValueError):
        HarnessConfig(feedback="verbose")
    with pytest.raises(ValueError):
        HarnessConfig(language="cobol")


def test_server_and_client_end_to_end(tmp_path):
    s = _session()
    srv = GraderServer(s)
    srv.start_background()
    try:
        write_client(tmp_path, srv.address)
        (tmp_path / "a.bf").write_text(print_text("Hello World!"))
        run = lambda *a: subprocess.run([sys.executable, "harness.py", *a], cwd=tmp_path,
                                        capture_output=True, text=True).stdout
        assert "Problem E01" in run("fetch")
        assert "OUTPUT: 'Hello World!'" in run("run", "a.bf")
        assert "SOLVED" in run("submit", "E01", "a.bf")
        assert request(srv.address, {"cmd": "status"})["solved"] == 1
    finally:
        srv.shutdown()
        srv.server_close()
