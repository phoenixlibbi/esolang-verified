#!/usr/bin/env python3
"""EsoLang-Bench evaluation harness.

Commands:
    init --language <lang>   Initialize session for 80 problems
    fetch                    Show next problem (no test cases)
    run <file> --input "x"   Run code with interpreter
    submit <id> <file>       Evaluate against hidden tests (max 3)
    status                   Progress dashboard
    skip                     Skip current problem
    export                   JSON export of all data
"""

import sys
sys.dont_write_bytecode = True  # don't leak source-path metadata via .pyc

import argparse
import json
import os
import shutil
import datetime

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------
# SCRIPT_DIR is the cell directory (where harness_state.json lives). When the
# harness is invoked through a symlink, abspath keeps the symlink path so the
# cell stays isolated.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# HARNESS_REAL_DIR follows the symlink to the actual harness location. We walk
# up from THAT directory to find the .experiment_root sentinel - that way one
# shared harness can be symlinked into many cell directories and each cell
# still reads the shared interpreters/public/private from the benchmark root.
HARNESS_REAL_DIR = os.path.dirname(os.path.realpath(__file__))


def _find_experiment_root():
    for start in (SCRIPT_DIR, HARNESS_REAL_DIR):
        d = start
        for _ in range(10):
            if os.path.exists(os.path.join(d, ".experiment_root")):
                return d
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    return HARNESS_REAL_DIR


_EXPERIMENTS_DIR = _find_experiment_root()

INTERPRETER_DIR = os.environ.get(
    "HARNESS_INTERPRETER_DIR",
    os.path.join(_EXPERIMENTS_DIR, "interpreters"),
)
PRIVATE_FILE = os.environ.get(
    "HARNESS_PRIVATE_FILE",
    os.path.join(_EXPERIMENTS_DIR, "private", "esolang_full_private.json"),
)
PUBLIC_FILE = os.environ.get(
    "HARNESS_PUBLIC_FILE",
    os.path.join(_EXPERIMENTS_DIR, "public", "esolang_full_public.json"),
)

STATE_FILE = os.path.join(SCRIPT_DIR, "harness_state.json")

MAX_SUBMISSIONS = 3
MAX_INTERPRETER_STEPS = 10_000_000

LANGUAGES = {
    "brainfuck": {
        "module": "brainfuck_interpreter",
        "class": "BrainfuckInterpreter",
        "ext": ".bf",
    },
    "befunge-98": {
        "module": "befunge98_interpreter",
        "class": "Befunge98Interpreter",
        "ext": ".b98",
    },
    "whitespace": {
        "module": "whitespace_interpreter",
        "class": "WhitespaceInterpreter",
        "ext": ".ws",
    },
    "shakespeare": {
        "module": "shakespeare_interpreter",
        "class": "ShakespeareInterpreter",
        "ext": ".spl",
    },
}

# Problem order: E01-E20, M01-M20, H01-H20, X01-X20
PROBLEM_ORDER = (
    [f"E{i:02d}" for i in range(1, 21)]
    + [f"M{i:02d}" for i in range(1, 21)]
    + [f"H{i:02d}" for i in range(1, 21)]
    + [f"X{i:02d}" for i in range(1, 21)]
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return None


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_private():
    with open(PRIVATE_FILE) as f:
        data = json.load(f)
    return {p["id"]: p for p in data["problems"]}


def load_public():
    with open(PUBLIC_FILE) as f:
        data = json.load(f)
    return {p["id"]: p for p in data["problems"]}


def get_interpreter(language):
    """Import and return an interpreter instance."""
    lang_info = LANGUAGES[language]
    # Add interpreter dir to path
    interp_dir = os.path.abspath(INTERPRETER_DIR)
    if interp_dir not in sys.path:
        sys.path.insert(0, interp_dir)
    mod = __import__(lang_info["module"])
    cls = getattr(mod, lang_info["class"])
    return cls(max_steps=MAX_INTERPRETER_STEPS)


def run_code(interpreter, code, input_data=""):
    """Run code and return (output, error_string_or_None)."""
    try:
        output = interpreter.run(code, input_data=input_data)
        return output, None
    except Exception as e:
        return None, str(e)


def ensure_log_dir(problem_id):
    log_dir = os.path.join(SCRIPT_DIR, "logs", problem_id)
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_init(args):
    if os.path.exists(STATE_FILE):
        print("ERROR: Session already initialized. Delete harness_state.json to reset.")
        sys.exit(1)

    language = args.language.lower()
    if language not in LANGUAGES:
        print(f"ERROR: Unknown language '{language}'. Choose from: {', '.join(LANGUAGES)}")
        sys.exit(1)

    state = {
        "language": language,
        "current_index": 0,
        "current_problem": None,
        "problems": {},
        "initialized_at": now_iso(),
    }
    # Initialize all 80 problems
    for pid in PROBLEM_ORDER:
        state["problems"][pid] = {
            "status": "pending",  # pending, active, solved, failed, skipped
            "submissions": [],
            "best_score": 0,
            "fetched_at": None,
            "finished_at": None,
        }
    save_state(state)
    print(f"Session initialized for {language}.")
    print(f"80 problems: E01-E20 (easy), M01-M20 (medium), H01-H20 (hard), X01-X20 (extra-hard)")
    print(f"Run 'python harness.py fetch' to get your first problem.")


def cmd_fetch(args):
    state = load_state()
    if state is None:
        print("ERROR: No session. Run 'python harness.py init --language <lang>' first.")
        sys.exit(1)

    # Finalize previous problem if any
    if state["current_problem"] is not None:
        prev_id = state["current_problem"]
        prev = state["problems"][prev_id]
        if prev["status"] == "active":
            if prev["best_score"] == 6:
                prev["status"] = "solved"
            elif len(prev["submissions"]) > 0:
                prev["status"] = "failed"
            else:
                prev["status"] = "skipped"
            prev["finished_at"] = now_iso()

    # Find next problem
    idx = state["current_index"]
    if idx >= len(PROBLEM_ORDER):
        print("All 80 problems have been completed!")
        save_state(state)
        return

    pid = PROBLEM_ORDER[idx]
    state["current_problem"] = pid
    state["current_index"] = idx + 1
    state["problems"][pid]["status"] = "active"
    state["problems"][pid]["fetched_at"] = now_iso()
    save_state(state)

    # Load public problem
    public = load_public()
    prob = public[pid]

    print(f"=" * 60)
    print(f"Problem {pid}: {prob['title']}")
    print(f"Difficulty: {prob['difficulty']}")
    print(f"=" * 60)
    print()
    print(prob["description"])
    print()
    print(f"No test cases provided. Generate your own test inputs from the description.")
    print(f"Use 'python harness.py run <file> --input \"data\"' to test.")
    print(f"Use 'python harness.py submit {pid} <file>' to evaluate (max {MAX_SUBMISSIONS} attempts).")


def cmd_run(args):
    state = load_state()
    if state is None:
        print("ERROR: No session initialized.")
        sys.exit(1)

    code_file = args.code_file
    if not os.path.exists(code_file):
        print(f"ERROR: File not found: {code_file}")
        sys.exit(1)

    with open(code_file) as f:
        code = f.read()

    input_data = args.input if args.input is not None else ""

    interpreter = get_interpreter(state["language"])
    output, error = run_code(interpreter, code, input_data)

    if error:
        print(f"RUNTIME ERROR: {error}")
    else:
        print(f"OUTPUT: {repr(output)}")


def cmd_submit(args):
    state = load_state()
    if state is None:
        print("ERROR: No session initialized.")
        sys.exit(1)

    pid = args.problem_id.upper()
    if pid not in state["problems"]:
        print(f"ERROR: Unknown problem ID '{pid}'.")
        sys.exit(1)

    prob_state = state["problems"][pid]
    if prob_state["status"] != "active":
        print(f"ERROR: Problem {pid} is not the current active problem.")
        sys.exit(1)

    if len(prob_state["submissions"]) >= MAX_SUBMISSIONS:
        print(f"ERROR: Maximum {MAX_SUBMISSIONS} submissions reached for {pid}.")
        sys.exit(1)

    code_file = args.code_file
    if not os.path.exists(code_file):
        print(f"ERROR: File not found: {code_file}")
        sys.exit(1)

    with open(code_file) as f:
        code = f.read()

    # Load hidden test cases
    private = load_private()
    test_cases = private[pid]["test_cases"]

    interpreter = get_interpreter(state["language"])

    results = []
    passed = 0
    for i, tc in enumerate(test_cases):
        output, error = run_code(interpreter, code, tc["input"])
        if error:
            status = "RUNTIME ERROR"
        elif output is not None and output.strip() == tc["output"].strip():
            status = "PASS"
            passed += 1
        else:
            status = "WRONG ANSWER"
        results.append(status)
        print(f"Hidden Test {i+1}: {status}")

    total = len(test_cases)
    attempt_num = len(prob_state["submissions"]) + 1
    print(f"\nScore: {passed}/{total}")

    if passed == total:
        print(f"SOLVED! Problem {pid} completed perfectly.")
        prob_state["status"] = "solved"
        prob_state["finished_at"] = now_iso()

    submission = {
        "attempt": attempt_num,
        "code_file": os.path.basename(code_file),
        "results": results,
        "passed": passed,
        "total": total,
        "submitted_at": now_iso(),
    }
    prob_state["submissions"].append(submission)
    if passed > prob_state["best_score"]:
        prob_state["best_score"] = passed

    # Save code and results to logs
    log_dir = ensure_log_dir(pid)
    ext = LANGUAGES[state["language"]]["ext"]
    shutil.copy2(code_file, os.path.join(log_dir, f"submission_{attempt_num}{ext}"))
    with open(os.path.join(log_dir, f"result_{attempt_num}.json"), "w") as f:
        json.dump(submission, f, indent=2)

    remaining = MAX_SUBMISSIONS - attempt_num
    if remaining > 0 and passed < total and prob_state["status"] == "active":
        print(f"Submissions remaining: {remaining}")

    save_state(state)


def cmd_status(args):
    state = load_state()
    if state is None:
        print("ERROR: No session initialized.")
        sys.exit(1)

    solved = 0
    failed = 0
    skipped = 0
    active = 0
    pending = 0
    total_passed = 0
    total_tests = 0

    for pid in PROBLEM_ORDER:
        ps = state["problems"][pid]
        s = ps["status"]
        if s == "solved":
            solved += 1
        elif s == "failed":
            failed += 1
        elif s == "skipped":
            skipped += 1
        elif s == "active":
            active += 1
        else:
            pending += 1
        total_passed += ps["best_score"]
        if ps["best_score"] > 0 or len(ps["submissions"]) > 0:
            total_tests += 6  # 6 test cases per problem

    print(f"Language: {state['language']}")
    print(f"=" * 40)
    print(f"Solved:    {solved}/80")
    print(f"Failed:    {failed}")
    print(f"Skipped:   {skipped}")
    print(f"Active:    {active}")
    print(f"Remaining: {pending}")
    print(f"=" * 40)
    attempted = solved + failed + skipped + active
    if total_tests > 0:
        print(f"Test cases passed: {total_passed}/{total_tests}")
    print(f"Current problem: {state['current_problem'] or 'None'}")


def cmd_skip(args):
    state = load_state()
    if state is None:
        print("ERROR: No session initialized.")
        sys.exit(1)

    if state["current_problem"] is None:
        print("ERROR: No active problem to skip.")
        sys.exit(1)

    pid = state["current_problem"]
    state["problems"][pid]["status"] = "skipped"
    state["problems"][pid]["finished_at"] = now_iso()
    print(f"Skipped problem {pid}.")
    print(f"Run 'python harness.py fetch' to get the next problem.")
    save_state(state)


def cmd_export(args):
    state = load_state()
    if state is None:
        print("ERROR: No session initialized.")
        sys.exit(1)

    export_file = os.path.join(SCRIPT_DIR, "export.json")
    with open(export_file, "w") as f:
        json.dump(state, f, indent=2)
    print(f"Exported session data to {export_file}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="EsoLang-Bench evaluation harness")
    subparsers = parser.add_subparsers(dest="command")

    p_init = subparsers.add_parser("init", help="Initialize session")
    p_init.add_argument("--language", required=True, help="Language: brainfuck, befunge-98, whitespace, shakespeare")

    p_fetch = subparsers.add_parser("fetch", help="Fetch next problem")

    p_run = subparsers.add_parser("run", help="Run code with interpreter")
    p_run.add_argument("code_file", help="Path to code file")
    p_run.add_argument("--input", default=None, help="Input data string")

    p_submit = subparsers.add_parser("submit", help="Submit solution")
    p_submit.add_argument("problem_id", help="Problem ID (e.g., E01)")
    p_submit.add_argument("code_file", help="Path to code file")

    p_status = subparsers.add_parser("status", help="Show progress")

    p_skip = subparsers.add_parser("skip", help="Skip current problem")

    p_export = subparsers.add_parser("export", help="Export session data")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "submit":
        cmd_submit(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "skip":
        cmd_skip(args)
    elif args.command == "export":
        cmd_export(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
