# EsoLang-Verified

**Unfamiliar-language coding tasks as verified RL environments for coding agents: audited tests, private test suites,
an isolated grader, a compiler for reference programs in Brainfuck, Befunge-98 and Whitespace, and Harbor packaging.
Every result in this README reproduces without running a model.**

[![CI](https://github.com/phoenixlibbi/esolang-verified/actions/workflows/ci.yml/badge.svg)](https://github.com/phoenixlibbi/esolang-verified/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![Tests](https://img.shields.io/badge/tests-647%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

```text
EsoLang-Bench (80 problems x 3 esolangs)
   │
   ├─ audit ──────► how many wrong programs do the tests let through?      160 / 512 match all 6 tests
   ├─ fresh ──────► private test suites from a secret seed                  catch 512 / 512
   ├─ esoc ───────► one IR program → Brainfuck · Befunge-98 · Whitespace    verified 70 · 80 · 80
   ├─ serve ──────► sequential protocol, grader in its own process          9 / 9 integrity probes no effect
   └─ harbor ─────► RL tasks: esorun · hidden tests · isolated verifier     oracle 1.0, no-op 0.0
```

## Contents

- [Why this exists](#why-this-exists)
- [Who is this for](#who-is-this-for)
- [Background](#background)
- [Key ideas, explained](#key-ideas-explained)
- [Results](#results)
- [Install](#install)
- [Quickstart](#quickstart-two-minutes-no-docker)
- [Usage](#usage)
- [Use it as an RL environment](#use-it-as-an-rl-environment)
- [How it maps to the paper](#how-it-maps-to-the-paper)
- [Design and security model](#design-and-security-model)
- [Limitations](#limitations)
- [Development](#development)
- [References](#references)

## Why this exists

A recent paper ([arXiv:2606.10933](https://arxiv.org/abs/2606.10933)) gives coding agents 80 short programming problems
that must be solved in esoteric languages, and finds that agents which sit within a few points of each other on
SWE-bench Verified spread from 11% to 99.7% here. The strongest agents adapt by *metaprogramming*: they write Python
that generates the Brainfuck instead of writing Brainfuck by hand.

That makes these tasks attractive **RL environments**: rewards are checkable, difficulty scales with the language, and the
skill separates agents. But a benchmark used to *rank* agents and an environment used to *train* them have different
needs. A training reward is optimized against, so it needs:

| An RL environment needs | Problem it targets | What this repo provides |
|---|---|---|
| Tests that reject wrong programs | Six tests per problem let common wrong programs through | `audit`: mutation scores per problem, with a failing input for each surviving wrong program |
| Tests a policy has not seen | The tests are public, so later models may have seen them | `fresh`: private suites from a secret seed, gated on the reference |
| A grader the policy cannot touch | File-based harnesses keep state and config in the agent's working area | `serve`: grader in its own process; `harbor`: isolated verifier container |
| Reference solutions | None existed in the target languages | `esoc` compiler + `oracles`: verified programs per language |
| Exact, fast execution | Grading many programs with slow interpreters | `interp`: step-exact interpreters, differential-tested |
| A gaming signal | No way to tell solving from gaming | `impossible`: variants with one contradicting test |

## Who is this for

- **RL / post-training teams** training coding agents: Harbor tasks with a binary reward (as in the paper) plus a
  partial-credit `fraction` for shaping, private seeds, isolated grading, and a difficulty ladder across three languages.
- **Evaluation teams**: re-test agents on private suites instead of public tests; measure gaming with impossible variants.
- **RL-environment builders**: reusable methods for any code environment: mutation-test your verifier, probe your harness,
  enforce limits in a separate process.
- **Researchers** studying agent adaptation to unfamiliar interfaces: `esoc` turns the paper's metaprogramming strategy
  into a tested compiler, and `serve` runs the paper's sequential protocol with configurable budgets and feedback.

### Typical workflows

```bash
# 1. How strong are the tests? (one command, a few seconds)
esoverified audit -v

# 2. Draw a private test suite for your lab and keep the seed secret
esoverified fresh --seed 418273 --out private_tests.json

# 3. Export RL tasks for Harbor with that seed, then check them with the oracle and a no-op agent
esoverified harbor --out tasks/ --languages befunge98 whitespace --seed 418273
harbor run -p tasks/ -a oracle      # expect reward 1.0
harbor run -p tasks/ -a nop         # expect reward 0.0

# 4. Run an agent through the paper's sequential protocol against the isolated grader
esoverified serve --language brainfuck --tests fresh --seed 418273 --workspace ./ws --export session.json
```

### Use in CI

```yaml
# fail the build if a task change lets wrong programs through the fresh suites
- run: pip install -e .
- run: esoverified audit --json audit.json
- run: python -c "import json; s=json.load(open('audit.json'))['summary']; assert s['score_fresh'] == 1.0"
```

## Background

**The paper** ([arXiv:2606.10933](https://arxiv.org/abs/2606.10933)) evaluates six coding agents (three model families, each
in its own harness: Claude Code, Codex, OpenCode) on EsoLang-Bench ([arXiv:2603.09678](https://arxiv.org/abs/2603.09678)):
80 problems in four tiers (easy to extra-hard), each with 6 hidden tests, in Brainfuck, Befunge-98, Whitespace and
Shakespeare. Agents run a sequential protocol: fetch a problem, run candidates locally as often as they like, submit up
to 3 times to the hidden tests, never revisit. Findings: unfamiliar languages separate agents far more than SWE-bench
does; strong agents write generators in a host language; forbidding that drops scores sharply; handing weaker agents
working helper code helps far more than describing the strategy in text.

**This repo** keeps the problems and the protocol and asks what is needed to use them as a training environment.

## Key ideas, explained

- **Mutation testing a verifier.** Write programs that are wrong in realistic ways (a value kept in one 8-bit cell, only
  the first digits parsed, the sign dropped, floor instead of truncating division) and count how many the tests accept.
  A wrong program only counts if it differs from the reference on at least one allowed input (equivalence filtering).
- **Gold-sanity gate.** Before any test is generated, the reference solution must reproduce every official test byte for byte.
- **Fresh, seeded tests.** Inputs come from per-problem generators that stay inside what the statement allows, plus
  hand-written edge cases; a canary string marks exported suites so they can be filtered from training data.
- **Differential testing.** The fast interpreters are run against the official ones on thousands of random programs;
  output, success, error kind and the step at which the 10M cap fires must all agree.
- **Privilege separation.** The grader owns tests, state and limits in its own process; the agent only has a client.
- **Metaprogramming as a compiler.** The paper's best agents built Python helpers that track the Brainfuck tape. `esoc`
  is that idea as a tested compiler: one IR program per problem, three backends.
- **Impossible variants.** One test contradicts the statement, so a solution that follows the statement cannot pass;
  any "solved" signals gaming (the ImpossibleBench idea).

## Results

All numbers come from `esoverified` 0.1.0 on EsoLang-Bench `a38a25f` (sha256-pinned). Full detail, witnesses and commands
in [docs/FINDINGS.md](docs/FINDINGS.md); every check is logged in [docs/VERIFICATION.md](docs/VERIFICATION.md); per-problem
datasheets in [docs/report/REPORT.md](docs/report/REPORT.md).

### 1. Test strength: six tests rank agents, but let wrong programs through

512 deliberately wrong programs (81 equivalent ones excluded):

| | |
|---|---|
| Wrong programs matching **all six tests** of their problem | **160 / 512 (31.2%)** |
| Problems with at least one such program | **74 / 80** |
| Mutation score, official tests | 68.8% |
| Mutation score, fresh suite (edge cases + 30 random inputs) | **100%** |

| Bug family | Wrong programs | Match official tests | Match fresh tests |
|---|---|---|---|
| value kept in one 8-bit cell | 64 | 35 | 0 |
| only the first k digits parsed / last digit printed | 122 | 41 | 0 |
| fixed-size input buffer | 56 | 42 | 0 |
| sign dropped | 31 | 10 | 0 |
| problem-specific logic slips | 158 | 29 | 0 |
| whitespace trimmed | 3 | 3 | 0 |
| off by one | 78 | 0 | 0 |

Examples: E19 asks for "truncating division toward zero" and floor division matches all six tests (input `-1 0` separates
them); M03's run-length encoding passes when counts above 9 print one digit; X16's Hamming distance passes when only the low
byte is compared. Weak tests can only make a score higher, so this does not affect rankings with large gaps; it matters
when the tests become a reward that a policy optimizes against.

### 2. Test availability and private suites

The 480 tests are publicly available (released with the dataset on 2026-03-07, as is standard), so models trained on public
data afterwards may have seen them. `esoverified fresh --seed N` produces private suites; every suite is generated only
after the reference passes the gold-sanity gate, and carries a canary GUID.

### 3. Grader isolation

| Harness | Integrity probes with an effect |
|---|---|
| File-based reference harness (state, config and tests reachable from the working directory) | 8 / 8 |
| esoverified grader process + client | **0 / 9** (a correct program is still graded SOLVED) |

The probes describe what a policy with shell access could change (state file, submission count, config paths, test file,
feedback detail, whitespace padding); they say nothing about any agent's behaviour.

### 4. Interpreters: fast and exact

| | |
|---|---|
| Random programs agreeing with the official interpreters (output, success, error kind) | **9,000 / 9,000** |
| Step at which `StepLimitExceeded` fires | identical (Brainfuck checked at 57 limits) |
| Spec dialect | documents where official Whitespace division and Befunge-98 fungespace differ from the language specs |

### 5. Reference programs (esoc)

| Language | Official tests | Fresh suite | Largest run |
|---|---|---|---|
| Whitespace | 80 / 80 | 80 / 80 | 0.4M steps |
| Befunge-98 | 80 / 80 | 80 / 80 | 7.1M steps |
| Brainfuck | 70 / 80 | 46 / 80 | within the 10M cap where verified |

Every Brainfuck miss is a step-limit timeout on long inputs (678 runs), never a wrong answer or error: random access on a
tape costs time proportional to the index. Verified Whitespace and Befunge-98 programs ship in [`oracles/`](oracles).

### 6. Harbor tasks in Docker

| Run | Tasks | Reward |
|---|---|---|
| Oracle agent, shared verifier | 12 | 1.0 on 12 / 12 |
| No-op agent, shared verifier | 12 | 0.0 on 12 / 12 |
| Oracle agent, isolated verifier | 4 | 1.0 on 4 / 4 |
| No-op agent, isolated verifier | 4 | 0.0 on 4 / 4 |

## Install

```bash
git clone https://github.com/phoenixlibbi/esolang-verified
cd esolang-verified
pip install -e ".[dev]"      # Python 3.10+, no runtime dependencies
```

Docker and [Harbor](https://github.com/laude-institute/harbor) are only needed to run exported tasks.

## Quickstart (two minutes, no Docker)

```bash
esoverified problems | head                     # the 80 problems
esoverified audit                               # 160/512 wrong programs match all official tests
esoverified probes                              # file-based harness vs isolated grader
esoverified compile E04 --language befunge98 -o e04.b98
esoverified run e04.b98 --input "5 -7"          # OUTPUT: '-2'
esoverified grade e04.b98 --problem E04 --seed 1234
python examples/scripted_session.py --language whitespace --problems E01 E04 M13
```

## Usage

### Audit test strength

```bash
esoverified audit [--problems E19 X04] [--json audit.json] [-v]
esoverified report --out report/ [--oracle-manifest oracles/manifest.json]   # per-problem datasheets
```

### Generate private tests

```bash
esoverified fresh --seed <secret> [--n-random 30] [--problems ...] --out tests.json
```

### Compile and verify reference programs

```bash
esoverified compile <PID> --language brainfuck|befunge98|whitespace [-o file]
esoverified oracles --out oracles/ --languages whitespace befunge98 brainfuck
```

### Run programs and grade them

```bash
esoverified run solution.bf --input "3 4" [--dialect official|spec]
esoverified grade solution.bf --problem E04 --tests official|fresh [--seed N] [--policy official|exact|newline]
```

### Run the sequential protocol

```bash
esoverified serve --language befunge98 --tests fresh --seed <secret> \
    [--max-submissions 3] [--run-budget 15] [--feedback aggregate|per_test] [--policy newline] \
    --workspace ./ws --log events.jsonl --export session.json
# in ./ws the agent runs: python harness.py fetch | run <file> --input ... | submit <ID> <file> | status | skip
```

### Integrity probes and interpreter checks

```bash
esoverified probes [--target official|hardened|both] [-v] [--json probes.json]
esoverified difftest [--cases 1000]
```

### Export Harbor tasks

```bash
esoverified harbor --out tasks/ --languages befunge98 whitespace brainfuck \
    --tests fresh|official|impossible --seed <secret> [--policy newline] [--shared-verifier]
```

## Use it as an RL environment

Each exported task is a standard Harbor task:

| Piece | Content |
|---|---|
| `instruction.md` | statement, the language reference card, I/O conventions, where to save the program |
| `environment/` | `python:3.12-slim` + `esorun`, the grader's interpreter as a CLI for unlimited local runs |
| `tests/` | hidden suite, the verifier's own interpreter copy, `verify.py` |
| `solution/` | the compiled oracle and `solve.sh` |
| reward | `reward.json = {"reward": 1.0 if every test passes else 0.0, "fraction": passed / total}` |

- **Isolated grading** is the default: the solution file is collected as an artifact, the agent's container is stopped, and
  `verify.py` runs in a fresh container built from `tests/`.
- **Binary reward** matches the paper's scoring; **`fraction`** gives a shaped signal for sparse-reward training.
- **Difficulty ladder**: the same 80 problems in Whitespace (easier), Befunge-98 and Brainfuck (hardest), across four tiers.
- **Fresh seeds per training run** keep tests out of reach of memorization; **impossible variants** measure gaming.
- **Prime Intellect `verifiers`**: the reward file uses the `reward` key read by its Harbor taskset adapter, with
  `fraction` recorded as a metric.
- Tasks are exported only if the oracle passes their own tests within the step cap; skipped ones are listed in `manifest.json`.

## How it maps to the paper

| Paper | In this repo |
|---|---|
| 80 problems, 4 tiers, 6 hidden tests | `dataset.py` (pinned) + `problems/` (reference, generator, edges for each) |
| Sequential protocol: fetch, local runs, 3 submissions, no revisits | `harness.py` `Session` + `serve` |
| Interpreters with a 10M step cap | `interp/` (step-exact) and `upstream/` (originals, pinned) |
| Language reference cards | `cards.py` (from the original prompts) |
| Metaprogramming (Python generators emitting Brainfuck) | `esoc/` compiler and `oracles` |
| Interpreter-call budget experiments | `--run-budget` |
| Aggregate vs detailed submission feedback | `--feedback aggregate` or `per_test` |
| Binary solved score | `reward`; plus `fraction` for RL shaping |

## Design and security model

```text
esoverified/
  dataset.py      pinned EsoLang-Bench copy (sha256 checked on load)
  upstream/       original interpreters, harness and prompts, unmodified (hashes pinned in tests)
  interp/         fast interpreters: bf, b98, ws; dialects "official" and "spec"
  difftest.py     differential fuzzing against the originals
  problems/       reference, generator, edge cases and mutants for all 80 problems
  freshtests.py   seeded suites, gold-sanity gate, canary
  mutants.py      generic esolang bug models + problem-specific slips
  audit.py        mutation-score audit
  impossible.py   one-contradicting-test variants
  harness.py      grader server + agent client
  probes.py       integrity probes
  esoc/           IR, library macros, 80 programs, backends ws / b98 / bf, simplifier, fuzzer
  oracles.py      compile + verify per language
  harbor.py       Harbor export (isolated verifier, reward + fraction)
  report.py       report cards
  cli.py          esoverified ...
```

- **Trust boundary**: everything that decides a score (tests, state, submission counts, run budgets, comparison policy)
  lives in the grader process or the verifier container. The agent's workspace contains only its programs and a client.
- **Supply chain**: the dataset and the original interpreters are vendored unmodified with pinned hashes; any change fails the tests.
- **Reproducibility**: no randomness without a seed; no model, network or API key needed for any result above.
- **Compiler internals**: Whitespace uses the heap for variables and the stack for expressions; Befunge-98 puts one basic
  block per row and jumps with `x`, storing values as bytes because the official fungespace keeps only bytes; Brainfuck tracks
  the tape pointer in Python, stores numbers as signed decimal digit blocks, walks arrays with a counter-carrying walker, and
  compares bytes with an O(x + c) layout trick. See [docs/DESIGN.md](docs/DESIGN.md).

## Limitations

- No model is run; results describe tests, graders and reference programs, not any agent's behaviour, and do not bear on the
  paper's conclusions.
- Mutants model common bugs; they are a lower bound on what weak tests accept, not an exhaustive search.
- Fresh inputs stay within what each statement clearly allows, and keep intermediate values below 2^46.
- Brainfuck reference programs exceed the 10M-step cap on long inputs for array-heavy problems; such tasks are not exported.
- Shakespeare (the paper's fourth language) is not compiled by `esoc`.
- Docker validation covered a 16-task sample; every exported task's oracle is checked locally with the same interpreter.

## Development

```bash
pytest -q              # 647 tests: everything except Docker and the slow sweeps
pytest -q -m slow      # all 80 Befunge-98 oracles on fresh suites, random Brainfuck programs
pytest -q -m docker    # Harbor oracle and no-op runs
```

CI runs the default suite on Python 3.10–3.13, the slow sweep on 3.12, plus `audit`, `probes` and the scripted session.

## References

1. Frontier Coding Agents Use Metaprogramming to Adapt to Unfamiliar Programming Languages. [arXiv:2606.10933](https://arxiv.org/abs/2606.10933)
2. EsoLang-Bench: Evaluating Genuine Reasoning in Large Language Models via Esoteric Programming Languages. [arXiv:2603.09678](https://arxiv.org/abs/2603.09678)
3. Why we no longer evaluate SWE-bench Verified. OpenAI, Feb 2026.
4. Auditing Reward Hackability in Code RL Training Environments. [arXiv:2606.16062](https://arxiv.org/abs/2606.16062)
5. Hardening Agent Benchmarks with Adversarial Hacker-Fixer Loops. [arXiv:2606.08960](https://arxiv.org/abs/2606.08960)
6. ImpossibleBench: Measuring LLMs' Propensity of Exploiting Test Cases. [arXiv:2510.20270](https://arxiv.org/abs/2510.20270)

## License

MIT. The EsoLang-Bench data (CC BY 4.0) and the original interpreters, harness and prompts (MIT) are vendored unmodified;
see [NOTICE.md](NOTICE.md).
