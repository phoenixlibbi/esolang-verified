# Design

```
esoverified/
  dataset.py        pinned EsoLang-Bench copy (sha256 checked on load)
  upstream/         the paper's interpreters, harness and prompts, unmodified (hashes pinned)
  interp/           fast interpreters: bf, b98, ws; dialects "official" and "spec"
  difftest.py       fuzz our interpreters against the official ones; list dialect gaps
  problems/         reference solution, input generator, edge cases, mutants for all 80 problems
  freshtests.py     seeded fresh suites, gold-sanity gate, canary
  mutants.py        generic esolang bug models + problem-specific slips
  audit.py          mutation-score audit of the official tests
  impossible.py     ImpossibleBench-style variants (one contradicting test)
  harness.py        hardened sequential harness: grader server + agent client
  probes.py         scripted integrity probes for a file-based harness and the grader process
  esoc/             compiler: IR, library macros, 80 programs, backends ws / b98 / bf
  oracles.py        compile + verify reference programs per language
  harbor.py         Harbor task export (isolated verifier, reward + fraction)
  report.py         per-problem report cards
  cli.py            `esoverified ...`
```

No runtime dependencies (standard library only). Python 3.10+.

## Interpreters

The official interpreters are slow for compiled programs (a 24 KB Brainfuck program running
millions of steps), and every audit, oracle check and Harbor verification runs many
programs, so `interp/` reimplements them:

* **Brainfuck** merges runs of `+-` and same-direction `<`/`>`, and runs "simple loops"
  (body of `+-<>` only, net pointer move 0, loop cell changing by exactly ±1) in one step.
  The step counter advances by exactly what the official interpreter would count (it
  checks `steps >= max_steps` before each instruction), so `StepLimitExceeded` fires at the
  same step. A negative-pointer dip inside a simple loop falls back to step-by-step replay.
* **Whitespace** and **Befunge-98** mirror the official control flow (including the
  non-standard `k`) instruction for instruction.

`tests/test_interp_diff.py` fuzzes all three against the vendored originals; any
disagreement in output, success or error kind fails the build.

## Problems, fresh tests and the audit

Each problem has a Python reference (`solve`), a generator (`gen`) that only produces
inputs the statement clearly allows, hand-written edge cases, tags that select generic
mutants, and 2 problem-specific mutants. Two gates keep this honest:

1. **gold sanity**: the reference must reproduce all six official tests *byte for byte*
   before any suite is built (it caught one misreading on the first run: X09 clamps the
   depth at zero, which only the official test `')))(('` reveals);
2. **equivalence filtering**: a mutant only counts if it differs from the reference on
   a 400+ input pool; otherwise it is "equivalent" and excluded.

Generator ranges are chosen so every intermediate value stays below 2^46 (all three
target languages are exact there; Befunge-98 storage and Whitespace division are not
beyond 2^53 on the official interpreters).

## Hardened harness

For RL the grader must be out of the policy's reach, so esoverified splits the protocol in two:

* `Session` (grader process) owns tests, state, submission caps, run budgets, feedback
  granularity and the comparison policy, and logs every event;
* the agent gets `harness.py`, a client that sends JSON requests over TCP and reads nothing
  that affects grading.

Same protocol as the paper (fixed forward order, 3 submissions, finalized problems never
revisited, unlimited local runs) unless configured. Knobs: `tests=official|fresh|impossible`,
`max_submissions`, `run_budget`, `feedback=aggregate|per_test`, `policy=official|exact|newline`.
In a container, run the grader as root and the agent as an unprivileged user.

## esoc: the compiler

The paper's strongest agents write Python that emits Brainfuck. esoc is that strategy as a
tested compiler:

* **IR** (`ir.py`): scalar variables, fixed-size integer arrays, `set / store / if / while /
  read_char / print_char / print_int`, pure expressions with `udiv`/`umod` on non-negative
  operands only. Signed division variants (`tdiv`, `tmod`, `fdiv`, `fmod`) are *library
  macros* (`lib.py`), so all three backends share one definition of rounding.
* **Whitespace backend**: heap for variables, stack for expressions, labels for control flow.
* **Befunge-98 backend**: one basic block per row starting with `>`; every jump is an
  absolute jump with `x` (push `dx, dy` = target - here) landing exactly on the target row's
  `>`; conditional jumps compute `dy` from the condition. Values are stored as `K` bytes of
  `v + 2^(8K-1)` because the official fungespace keeps only bytes; arrays are zeroed at start
  because fungespace starts as spaces.
* **Brainfuck backend**: a Python emitter tracks the pointer and allocates cells (like the
  `bflib.py` Opus built in the paper). Numbers are signed decimal blocks `[sign, d0..dD-1]`;
  add, subtract, compare, multiply and long division work digit by digit, with fast paths
  for constants (increment, multiply by 2..10, divide by 2..25), comparisons with 0, and
  byte variables (characters live in one cell; 0 encodes EOF). Byte comparison uses the
  classic O(x + c) layout trick (`[->-]>[...]` on `[f, p, 1, 0]`), tested exhaustively.
  Arrays are rows of records walked by a carrier holding the index as decimal counters.
  Layout: `[byte vars][trick cells][scratch][flags][temporaries][variables][arrays]`, sized
  by a first compilation pass so hot copies travel short distances.
* **Simplifier**: constant folding so `tdiv(x, 2)` reaches the constant fast path.

Correctness evidence: random IR programs (`esoc/fuzz.py`) agree with the IR interpreter on
all three backends; all 80 programs agree with the Python references on the official and
fresh tests (IR level); compiled oracles are verified per language (`oracles.py`).

## Harbor tasks

`esoverified harbor` writes one task per (language, problem): instruction (statement,
the paper's language card, I/O conventions), a `python:3.12-slim` environment with
`esorun` (the grader's interpreter as a CLI, unlimited local runs), `tests/` with the hidden
suite, its own interpreter copy and `verify.py`, and `solution/` with the oracle.

* **Isolated grading** (default): `artifacts = ["/app/solution.<ext>"]` and
  `[verifier] environment_mode = "separate"`, so Harbor stops the agent's container and
  grades in a fresh one; nothing the agent left running can reach the tests.
* **Reward**: `reward.json = {"reward": 1 if every test passes else 0, "fraction": k/n}`,
  the binary score the paper uses plus partial credit for RL shaping. This is the format
  Prime Intellect `verifiers`' Harbor taskset reads (`reward` key, other numbers recorded
  as metrics).
* Tasks whose oracle does not pass their own tests within the step cap are skipped and
  listed in `manifest.json`.
