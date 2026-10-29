import json
import subprocess
import sys
from pathlib import Path

import pytest

from esoverified.cli import main
from esoverified.harbor import export_tasks
from esoverified.oracles import check_oracle


def _verify_locally(task: Path, solution: str, tmp: Path) -> dict:
    """Run the task's verify.py with its container paths mapped to temp dirs."""
    app, logs = tmp / "app", tmp / "logs"
    app.mkdir(parents=True, exist_ok=True)
    ext = next((task / "solution").glob("oracle.*")).suffix
    (app / f"solution{ext}").write_text(solution)
    code = (task / "tests" / "verify.py").read_text()
    code = code.replace('"/tests"', repr(str(task / "tests"))).replace('"/tests/hidden.json"',
                                                                      repr(str(task / "tests" / "hidden.json")))
    code = code.replace('"/app/solution', f'"{app}/solution').replace('"/logs/verifier"', repr(str(logs)))
    script = tmp / "verify_local.py"
    script.write_text(code)
    subprocess.run([sys.executable, str(script)], check=True, capture_output=True)
    return json.loads((logs / "reward.json").read_text())


def test_export_and_verify_tasks(tmp_path):
    m = export_tasks(tmp_path / "tasks", ["whitespace", "befunge98"], ["E04", "M01"], seed=99)
    assert sorted(m["tasks"]) == ["esolang-b98-e04", "esolang-b98-m01", "esolang-ws-e04", "esolang-ws-m01"]
    task = tmp_path / "tasks" / "esolang-b98-e04"
    for f in ("task.toml", "instruction.md", "environment/Dockerfile", "environment/esorun/__main__.py",
              "tests/test.sh", "tests/verify.py", "tests/hidden.json", "tests/esorun/common.py",
              "solution/solve.sh", "solution/oracle.b98"):
        assert (task / f).exists(), f
    assert "Language Reference" in (task / "instruction.md").read_text()
    assert "hidden" not in (task / "environment" / "Dockerfile").read_text()
    toml = (task / "task.toml").read_text()
    assert 'environment_mode = "separate"' in toml and '"/app/solution.b98"' in toml   # isolated grading
    assert "COPY . /tests" in (task / "tests" / "Dockerfile").read_text()
    oracle = (task / "solution" / "oracle.b98").read_text()
    assert _verify_locally(task, oracle, tmp_path / "a") == {"reward": 1.0, "fraction": 1.0}
    r = _verify_locally(task, "@", tmp_path / "b")
    assert r["reward"] == 0.0 and r["fraction"] < 1.0


def test_shared_verifier_option(tmp_path):
    export_tasks(tmp_path / "t", ["whitespace"], ["E01"], seed=1, isolated=False)
    task = tmp_path / "t" / "esolang-ws-e01"
    assert "environment_mode" not in (task / "task.toml").read_text()
    assert not (task / "tests" / "Dockerfile").exists()


def test_impossible_tasks_reward_zero_for_the_oracle(tmp_path):
    m = export_tasks(tmp_path / "t", ["whitespace"], ["E04"], tests_mode="impossible", seed=5)
    task = tmp_path / "t" / m["tasks"][0]
    r = _verify_locally(task, (task / "solution" / "oracle.ws").read_text(), tmp_path / "c")
    assert r["reward"] == 0.0 and 0 < r["fraction"] < 1


def test_unverified_oracle_is_skipped(tmp_path, monkeypatch):
    import esoverified.harbor as H
    monkeypatch.setattr(H, "compile_problem", lambda pid, lang: "@")   # a wrong oracle
    m = export_tasks(tmp_path / "t", ["befunge98"], ["E04"], seed=1)
    assert m["tasks"] == [] and m["skipped_unverified_oracle"][0]["pid"] == "E04"


def test_check_oracle():
    chk = check_oracle("E04", "whitespace")
    assert chk.verified_official and chk.verified_fresh


def test_report_cards(tmp_path):
    main(["report", "--out", str(tmp_path), "--problems", "E19", "E04"])
    data = json.loads((tmp_path / "report_cards.json").read_text())
    e19 = next(c for c in data["cards"] if c["pid"] == "E19")
    assert any(m["mutant"] == "floor_division" for m in e19["surviving_mutants"])
    assert e19["impossible_variant_ok"]
    assert "floor_division" in (tmp_path / "REPORT.md").read_text()


def test_cli_compile_run_grade(tmp_path, capsys):
    out = tmp_path / "e04.ws"
    assert main(["compile", "E04", "--language", "ws", "-o", str(out)]) == 0
    assert main(["run", str(out), "--input", "2 3"]) == 0
    assert "OUTPUT: '5'" in capsys.readouterr().out
    assert main(["grade", str(out), "--problem", "E04", "--tests", "official"]) == 0
    assert main(["grade", str(out), "--problem", "E04", "--seed", "3"]) == 0


def test_cli_audit_fresh_problems(tmp_path, capsys):
    assert main(["audit", "--problems", "E19", "--json", str(tmp_path / "a.json")]) == 0
    assert "pass all official tests" in capsys.readouterr().out
    assert main(["fresh", "--seed", "7", "--problems", "E04", "--out", str(tmp_path / "f.json")]) == 0
    d = json.loads((tmp_path / "f.json").read_text())
    assert d["seed"] == 7 and "canary" in d and d["problems"]["E04"]["tests"]
    assert main(["problems"]) == 0


@pytest.mark.docker
def test_harbor_oracle_and_nop_in_docker(tmp_path):
    export_tasks(tmp_path / "tasks", ["befunge98"], ["E04"], seed=3)
    for agent, want in (("oracle", "1.0"), ("nop", "0.0")):
        r = subprocess.run(["harbor", "run", "-p", str(tmp_path / "tasks"), "-a", agent, "-o",
                            str(tmp_path / f"jobs-{agent}")], capture_output=True, text=True, timeout=1800)
        assert r.returncode == 0, r.stdout[-2000:]
        rewards = [json.loads(p.read_text()) for p in (tmp_path / f"jobs-{agent}").rglob("reward.json")]
        assert rewards and all(str(x["reward"]) == want for x in rewards)
