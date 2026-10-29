# EsoLang-Verified

**An audited, contamination-resistant release of [EsoLang-Bench](https://huggingface.co/datasets/Lossfunk/Esolang-Bench)
for coding-agent RL and evals, with hardened grading, reference programs in Brainfuck,
Befunge-98 and Whitespace, and Harbor packaging. Every result is reproducible without running a model.**

Built on *"Frontier Coding Agents Use Metaprogramming to Adapt to Unfamiliar Programming Languages"*
([arXiv:2606.10933](https://arxiv.org/abs/2606.10933)) and EsoLang-Bench ([arXiv:2603.09678](https://arxiv.org/abs/2603.09678)).
The paper shows that unfamiliar languages separate coding agents far more than SWE-bench does, and that the best
agents win by writing *generators* in Python instead of writing Brainfuck by hand. That makes these tasks attractive
RL environments. A benchmark used to *rank* agents and an environment used to *train* them have different needs:
a training reward is optimized against, so its tests, its grader and its reference solutions must hold up to a
policy searching for shortcuts. This repository measures those properties and adds what an RL environment needs.

## Results

| | Result |
|---|---|
| **Test strength** | **160 of 512 deliberately wrong programs (31.2%) pass all six tests** of their problem, in **74 of 80 problems**. A fresh suite (edge cases + 30 random inputs) catches all 512. Six tests rank agents well; as an RL reward, a policy would be paid for these shortcuts. |
| **Example** | E19 asks for "truncating division toward zero"; a floor-division program passes all six tests. The input `-1 0` tells them apart. |
| **Test availability** | The 480 tests are publicly available (released with the dataset in March 2026, as is standard), so models trained later may have seen them. `esoverified fresh` draws private suites from a secret seed. |
| **Grader isolation** | For RL, grading must be out of the policy's reach. 8 scripted integrity probes show what a policy with shell access could change in a file-based harness (state file, submission count, config paths, test file, feedback detail, whitespace). esoverified's grader runs as a separate process; **9/9 probes have no effect**. |
| **Interpreters** | Fast reimplementations agree with the official interpreters on **9,000 fuzzed programs**, including the exact step where the 10M cap fires. A `spec` dialect documents where the official Whitespace and Befunge-98 semantics differ from the language specs. |
| **Reference programs** | The `esoc` compiler produces verified reference programs for **80/80 problems in Whitespace and Befunge-98** (official + fresh tests) and **70/80 in Brainfuck on the official tests** (46/80 on fresh suites within the 10M-step cap; every miss is a timeout, never a wrong answer). |
| **Harbor** | Exported tasks run in Docker: the oracle agent scores **1.0 on 16/16 tasks** and the no-op agent **0.0 on 16/16** (shared and isolated verifier modes). |

Details, witnesses and commands: [docs/FINDINGS.md](docs/FINDINGS.md). Per-problem datasheets:
[docs/report/REPORT.md](docs/report/REPORT.md). Evidence log: [docs/VERIFICATION.md](docs/VERIFICATION.md).

## What's inside

| Component | What it gives you |
|---|---|
| `esoverified audit` | Mutation-score audit: which wrong programs each problem's tests let through, with a failing input for each. |
| `esoverified fresh --seed N` | Private test suites from a secret seed, gated on the reference reproducing all official tests exactly; canary string included. |
| `esoverified probes` | Scripted integrity probes for a file-based harness (the reference layout) and for esoverified's grader. |
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
esoverified probes -v                      # integrity probes: file-based harness vs grader process
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
* **Environment builders**: mutation testing of verifiers, scripted integrity probes, and the "enforce, don't
  instruct" harness design apply to any code RL environment.

## Scope and limits

* No model is run here, and nothing here is a claim about any agent's behaviour or about the paper's
  conclusions: weak tests can only make a score higher, not create the paper's large gaps between agents.
  The point is the difference between a ranking benchmark and an RL reward.
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
