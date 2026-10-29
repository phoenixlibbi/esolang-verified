# Verification log

What was run to check each claim, and what came out. Machine: macOS, Python 3.14 (CI: 3.10–3.13),
Docker 29.6, Harbor 0.20.0. Data: EsoLang-Bench `a38a25f` (sha256 pinned); paper code `b93ef26` (hashes pinned).

## Test suite

```bash
pytest -q                 # default: everything except Docker and the slow full sweeps
pytest -q -m slow         # all 80 Befunge-98 oracles on fresh suites, random Brainfuck programs
pytest -q -m docker       # Harbor oracle + nop runs in Docker
```

The default suite covers dataset integrity and pinned upstream hashes, interpreter differential fuzzing
(1,500 programs per language), the gold-sanity gate for all 80 references, generator validity, the audit
mechanics, the hardened harness protocol, both probe batteries, impossible variants for all 80 problems
(both modes), the IR programs for all 80 problems on official + fresh tests, all 80 Whitespace oracles,
selected Befunge-98 and Brainfuck oracles (Befunge-98 also under the spec dialect), exhaustive checks of
the Brainfuck byte comparison, random-program differential tests of the backends, Harbor export with local
verification (oracle 1.0, wrong program 0.0, impossible variant 0.0 for the oracle), report cards and the CLI.

## Interpreters

| Check | Result |
|---|---|
| `difftest.fuzz`, 3,000 random programs per language vs the vendored official interpreters | 9,000 / 9,000 agree (output, success, error kind) |
| Brainfuck step cap: same program at 57 different limits | `StepLimitExceeded` at exactly the same step as the official interpreter |
| Dialect gaps (official vs spec) | Brainfuck: none. Whitespace: division precision and rounding. Befunge-98: byte cells, bounded space, division by zero (see FINDINGS §4) |

## Public-test timeline

| Check | Result |
|---|---|
| Hugging Face `Lossfunk/Esolang-Bench` first data commit (`74c5e6d`, "v1.0", 2026-03-07) | `data/test.jsonl` sha256 = pinned copy (`04ce0dbf…`): the tests were public from the first release |
| GitHub `Lossfunk/EsolangBench` first version of `esolang_benchmark.json` (2026-03-07) | 80 problems, `input_output_examples` = the graded tests |
| `Lossfunk/esolang-metaprogramming` (reference harness) created | 2026-06-08 |

## Problems, fresh tests, audit

| Check | Result |
|---|---|
| Reference reproduces all 6 official tests byte for byte | 80 / 80 (one misreading caught and fixed: X09 clamps depth at 0) |
| Generators and edges produce inputs the reference handles | 80 / 80 (200 random + all edges each) |
| `esoverified audit` | 512 valid wrong programs; 160 pass all official tests (74 problems); fresh suites catch 512/512 |
| First audit run, before two edge categories were added | fresh suites caught 510/512 (M19 leading space, X20 three-digit K) |

## Harness probes

| Target | Result |
|---|---|
| File-based reference harness, rebuilt as its setup script lays it out, real tests in `private/` | 8 / 8 probes change the recorded result or grading inputs |
| esoverified grader server + client | 9 / 9 probes have no effect; a correct program is still SOLVED |

## esoc and oracles

| Check | Result |
|---|---|
| IR programs vs Python references (official + fresh seed 0 + 150 pool inputs) | 80 / 80 |
| Random IR programs vs IR interpreter | Whitespace 120/120, Befunge-98 120/120, Brainfuck 30/30 runs |
| Whitespace oracles, official + fresh, official interpreter semantics | 80 / 80 (max 0.4M steps) |
| Befunge-98 oracles, official + fresh | 80 / 80 (max 7.1M steps of 10M) |
| Brainfuck oracles, official tests within 10M steps | 70 / 80 |
| Brainfuck oracles, official + fresh within 10M steps | 46 / 80 |
| Brainfuck failures by kind (34 problems with any miss, official + fresh) | 678 step-limit timeouts, **0 wrong answers, 0 errors**; 711 tests pass |

## Harbor (Docker)

| Run | Tasks | Result |
|---|---|---|
| `harbor run -a oracle`, shared verifier | 12 (E01, E04, M01, X13 × 3 languages) | 12 × reward 1.0 |
| `harbor run -a nop`, shared verifier | same 12 | 12 × reward 0.0 |
| `harbor run -a oracle`, isolated verifier (`environment_mode = "separate"`, solution passed as artifact) | 4 (E04, X13 × Befunge-98, Whitespace) | 4 × reward 1.0, verifier log `passed 36/36` |
| `harbor run -a nop`, isolated verifier | same 4 | 4 × reward 0.0 |
