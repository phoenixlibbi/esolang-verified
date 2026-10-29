# EsoLang-Verified

**An audited, contamination-resistant release of [EsoLang-Bench](https://huggingface.co/datasets/Lossfunk/Esolang-Bench)
for coding-agent RL and evals, with hardened grading, reference programs in Brainfuck,
Befunge-98 and Whitespace, and Harbor packaging. Every result is reproducible without running a model.**

Built on *"Frontier Coding Agents Use Metaprogramming to Adapt to Unfamiliar Programming Languages"*
(Sharma, Thorat & Chopra, 2026, [arXiv:2606.10933](https://arxiv.org/abs/2606.10933)), which shows that
unfamiliar languages separate coding agents far more than SWE-bench does, and that the best agents win by
writing *generators* in Python instead of writing Brainfuck by hand. That makes these tasks attractive RL
environments. This repository checks whether the environment itself can be trusted, and fixes what it finds.

## Findings

| | Result |
|---|---|
| **Hidden tests** | The paper's code (June 2026) redacts the 6 hidden tests per problem, but all 480 have been public since EsoLang-Bench's release (2026-03-07) on Hugging Face and GitHub, so later models may have seen them. |
| **Test strength** | **160 of 512 deliberately wrong programs (31.2%) pass all six official tests**, in **74 of 80 problems**. A fresh suite (edge cases + 30 random inputs) catches all 512. |
| **Statement vs tests** | E19 and X04 require "truncating division toward zero"; a floor-division program passes every official test of both. |
| **Official harness** | **8 scripted exploits succeed from the agent's own shell**: forging `harness_state.json` to mark problems solved, resetting the submission cap, planting a sentinel or an env var so the harness grades against the agent's own tests or interpreter, reading the test file, per-test feedback, and whitespace-padded output passing. |
| **Hardened harness** | The same exploits plus a client-redirect attack: **9/9 blocked** by a grader that runs as a separate process. |
| **Interpreters** | Fast reimplementations agree with the official interpreters on **9,000 fuzzed programs**, including the exact step where the 10M cap fires. The official Whitespace and Befunge-98 interpreters deviate from their specs (float division, byte-only fungespace). |
| **Reference programs** | The benchmark ships none. The `esoc` compiler produces verified oracles for **80/80 problems in Whitespace and Befunge-98** (official + fresh tests) and **70/80 in Brainfuck on the official tests** (46/80 on fresh suites within the 10M-step cap; every miss is a timeout, never a wrong answer). |
| **Harbor** | Exported tasks run in Docker: the oracle agent scores **1.0 on 16/16 tasks** and the no-op agent **0.0 on 16/16** (shared and isolated verifier modes). |

Details, witnesses and commands: [docs/FINDINGS.md](docs/FINDINGS.md). Per-problem datasheets:
[docs/report/REPORT.md](docs/report/REPORT.md). Evidence log: [docs/VERIFICATION.md](docs/VERIFICATION.md).

## What's inside

| Component | What it gives you |
|---|---|
| `esoverified audit` | Mutation-score audit: which wrong programs each problem's tests let through, with a failing input for each. |
| `esoverified fresh --seed N` | Private test suites from a secret seed, gated on the reference reproducing all official tests exactly; canary string included. |
| `esoverified probes` | Scripted exploits against the paper's harness (rebuilt exactly as its setup script lays it out) and against esoverified's. |
| `esoverified serve` | The paper's sequential protocol (fixed order, 3 hidden submissions, no revisits) as a grader server plus an agent client; knobs for test source, run budget, feedback granularity and comparison policy. |
| `esoverified compile PID --language L` | `esoc`, a compiler from a small IR to all three esolangs: the paper's metaprogramming strategy as a tested tool. |
| `esoverified oracles` | Compile and verify reference programs for every problem and language. The verified Whitespace and Befunge-98 programs ship in [`oracles/`](oracles) with a manifest of their checks; Brainfuck oracles are generated on demand (they run to megabytes). |
| `esoverified harbor` | One Harbor task per language and problem: `esorun` for unlimited local runs, hidden tests, isolated grading, `reward` (binary, as in the paper) + `fraction` (partial credit). Impossible variants for measuring cheating. |
| `esoverified difftest` | Differential fuzzing of the interpreters against the official ones. |
| `esoverified report` | Per-problem report cards (JSON + Markdown). |

## Quickstart

```bash
pip install -e ".[dev]"
esoverified audit                          # 160/512 wrong programs pass the official tests
esoverified probes -v                      # 8 exploits on the official harness, 0 on the hardened one
esoverified compile E04 --language befunge98 -o e04.b98
esoverified grade e04.b98 --problem E04 --seed 1234
esoverified harbor --out tasks/ --languages befunge98 whitespace --seed <secret>
harbor run -p tasks/ -a oracle              # needs Docker; expect reward 1.0
```

Run a model-free agent session against the hardened grader:

```bash
esoverified serve --language brainfuck --tests fresh --seed <secret> --workspace ./ws --export session.json
# the agent works in ./ws and calls: python harness.py fetch | run <file> --input ... | submit <ID> <file>
```

## Who it is for

* **RL teams**: verified tasks with oracles, a binary reward plus `fraction` for shaping, isolated grading,
  and fresh seeds so a policy cannot memorize the tests. Difficulty varies with language (Whitespace is easy,
  Brainfuck is hard) on the same 80 problems.
* **Eval teams**: re-test agents on private suites instead of the public tests, and run impossible variants
  to measure how often an agent games the grader (as in ImpossibleBench).
* **Environment builders**: mutation testing of verifiers, scripted exploit probes, and the "enforce, don't
  instruct" harness design apply to any code RL environment.

## Scope and limits

* No model is run here. The findings are about the benchmark and harness, not about any agent; nothing
  suggests the paper's agents exploited the harness, and none of this undermines the paper's conclusions:
  weak tests can only inflate scores, not create its large gaps between agents. The tests were published
  by the authors with EsoLang-Bench on 2026-03-07, standard practice for benchmarks; the risk is for models
  trained after that, and for using the tests as an RL training reward.
* Mutants model common bugs (8-bit cells, digit limits, fixed buffers, sign handling, plus two
  problem-specific slips per problem). They are a lower bound on what weak tests let through, not an
  exhaustive search.
* Fresh inputs stay within what each statement clearly allows, and keep intermediate values below 2^46.
* Brainfuck oracles are correct but exceed the 10M-step cap on long inputs for array-heavy problems
  (tape random access costs time proportional to the index). The Harbor exporter only emits tasks whose
  oracle passes its own tests within the cap.
* Shakespeare (the paper's fourth language) is not compiled by `esoc`.

## Credits and licence

MIT for this repository. The EsoLang-Bench data (CC BY 4.0) and the paper's interpreters, harness and prompts
(MIT) are vendored unmodified with pinned hashes; see [NOTICE.md](NOTICE.md).
Related work this builds on: OpenAI's audit of SWE-bench Verified (Feb 2026), *Auditing Reward Hackability in Code
RL Training Environments* (arXiv:2606.16062), *Hardening Agent Benchmarks with Adversarial Hacker-Fixer Loops*
(arXiv:2606.08960), and ImpossibleBench (ICLR 2026).
