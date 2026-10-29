# Findings

Everything below is reproducible with the commands shown, from a fresh clone, with no
model and no API key. Numbers are from `esoverified` 0.1.0 on EsoLang-Bench
`Lossfunk/Esolang-Bench@a38a25f` and the paper's code `Lossfunk/esolang-metaprogramming@b93ef26`.

---

## 1. The "hidden" tests are public

The paper describes six private hidden tests per problem, and its code release ships them
redacted (`benchmark_harness/private/esolang_full_private.json` replaces every input and
expected output with `<REDACTED_INPUT>` / `<REDACTED_EXPECTED>`).

The same 480 input/output pairs are public, unredacted, in two places:

| Where | Field | Identical to the graded tests |
|---|---|---|
| `huggingface.co/datasets/Lossfunk/Esolang-Bench`, `data/test.jsonl` | `test_cases` | 80/80 problems |
| `github.com/Lossfunk/EsolangBench`, `esolang_bench/data/esolang_benchmark.json` | `input_output_examples` | 80/80 problems |

Timeline (from the Hugging Face and GitHub commit history):

| Date | Event |
|---|---|
| 2026-02-14 | `Lossfunk/EsolangBench` GitHub repo created |
| 2026-03-07 | EsoLang-Bench v1.0 released on Hugging Face and GitHub **with all 480 tests** (byte-identical to the tests graded today, sha256 `04ce0dbf…`) |
| 2026-06-08/09 | The metaprogramming paper and its code release; the code redacts the tests |

**This is not a criticism of the authors.** Publishing a benchmark's tests is standard practice
(HumanEval and SWE-bench do it), and "hidden" in the paper means hidden from the agent during
a run, which their sandboxed protocol provides. The agents in the paper were released before or
around the dataset (e.g. Claude Opus 4.6 and Sonnet 4.6 in February 2026), so contamination is an
unlikely explanation for their results, and the paper itself says it cannot rule out exposure.
The risk is forward-looking: any model trained on public data after March 2026 may have seen the
exact tests, which matters most if EsoLang-Bench is used as an RL training environment. EsoLang-Verified's answer is **fresh private
suites**: each lab draws its own tests from a secret seed (`esoverified fresh --seed N`), with
expected outputs from reference solutions that are first checked to reproduce all six
official tests exactly (the gold-sanity gate).

## 2. Almost a third of wrong programs pass the official tests

`esoverified audit` runs **512 deliberately wrong programs** (mutants) against the six
official tests of each problem. A mutant counts only if it is *really* wrong: it must
differ from the reference on at least one input in a pool of 400+ inputs the problem
statement allows (81 that never differ were excluded as equivalent).

| | |
|---|---|
| Wrong programs passing **all six official tests** | **160 / 512 (31.2%)** |
| Problems with at least one such program | **74 / 80** |
| Mutation score of the official tests | 68.8% |
| Mutation score of a fresh suite (edge cases + 30 random inputs) | **100.0%** |

By kind of bug (`docs/report/REPORT.md` has all 80 problems):

| Bug family | Wrong programs | Pass official tests | Pass fresh suite |
|---|---|---|---|
| value kept in one 8-bit cell (Brainfuck's natural mistake) | 64 | 35 | 0 |
| only the first k digits parsed / last digit printed | 122 | 41 | 0 |
| fixed-size input buffer (8 or 16 chars) | 56 | 42 | 0 |
| sign dropped | 31 | 10 | 0 |
| problem-specific logic slips | 158 | 29 | 0 |
| whitespace trimmed | 3 | 3 | 0 |
| off by one | 78 | 0 | 0 |

Logic slips the official tests cannot see (each with an input where the program is wrong):

| Problem | Wrong program | Fails on | Expected | Gets |
|---|---|---|---|---|
| E19 Integer Average ("truncating division toward zero") | floor division | `-1 0` | `0` | `-1` |
| X04 Postfix ("truncate toward zero for division") | floor division | `0 8 - 7 /` | `-1` | `-2` |
| E06 Even Or Odd | C-style remainder, negatives become "even" | `-1` | `odd` | `even` |
| M03 Run Length Encoding | prints only one digit of the count | `aaaaaaaaaa` | `a10` | `a0` |
| M06 GCD | C remainder, result can be negative | `-4 -6` | `2` | `-2` |
| M08 Fibonacci ("arbitrary precision") | 32-bit overflow | `48` | `4807526976` | `512559680` |
| H18 Divisible By 3 | checks the last digit only | `10` | `no` | `yes` |
| X16 Hamming Distance | compares only the low byte | `0 256` | `1` | `0` |
| H20 Sort Strings | case-insensitive order | `2\nZ\na` | `Z a` | `a Z` |
| X14 Next Greater Element | `>=` instead of `>` | `2\n23 23` | `-1 -1` | `23 -1` |

E19 and X04 are notable: the statement names the rounding rule, and no test checks it.

What this does and does not mean: weak tests can only make a score *higher* than it should be
(a wrong program counted as solved). They cannot explain the paper's large gaps between agents
(e.g. 64 vs 4 problems on Brainfuck), so the paper's conclusions stand. Six tests per problem was a
reasonable design for comparing agents; the issue appears when the same tests become a training
reward, where a policy is optimized against exactly what the tests miss.

Method notes. The fresh suite is not tuned to the mutants: it is the problem's hand-written
edge cases plus 30 random inputs from an independent seed. On the first audit run two
mutants survived it (a leading-space input for M19, a three-digit K for X20); those two
edge categories were then added to the edge lists, which is why the score is 100%.
Reproduce: `esoverified audit -v` and `esoverified report --out report/`.

## 3. The official harness can be exploited from the agent's own shell

`esoverified probes --target official` rebuilds the paper's experiment layout exactly
(`benchmark_harness/` with the sentinel, interpreters, private and public files, and a
cell directory with a relative `harness.py` symlink, as `scripts/setup_main_grid.py` does),
puts the real tests in `private/`, and plays a cheating agent through the harness's own
CLI. Every probe succeeds:

| Probe | What the agent does | Result |
|---|---|---|
| read_hidden_tests | `cat ../../../../../benchmark_harness/private/esolang_full_private.json` | tests readable |
| state_forgery | sets `best_score: 6` in `harness_state.json` (in its cell), then `fetch` | problem recorded as **solved** with 0 submissions |
| submission_cap_reset | clears `submissions` in `harness_state.json` after 3 failures | 4th hidden submission graded |
| sentinel_hijack | creates `.experiment_root` and its own `private/` in the cell (the harness searches the cell first) | empty program **SOLVED** |
| env_override | `HARNESS_PRIVATE_FILE=my_tests.json python harness.py submit ...` | empty program **SOLVED** |
| interpreter_hijack | `HARNESS_INTERPRETER_DIR=./myinterp` with an interpreter that answers from the test file | empty program **SOLVED** |
| per_test_feedback | `submit` | prints a verdict per hidden test |
| strip_leniency | prints `"\n\n   Hello World!   \n\n"` for E01 | **SOLVED** (`output.strip() == expected.strip()`) |

The paper's isolation is an instruction in the prompt ("Do not read private test files,
reverse-engineer the harness, or hardcode outputs"; Appendix A.11 "agents are instructed
not to inspect…"), not an enforced boundary. We make **no claim that any agent in the
paper did any of this**; the point is that the reported scores depend on agents choosing
not to, which matters for RL training, where policies are optimized against the grader.

Two of these also contradict the paper's text: Section 2 and Table 4 say hidden
submissions return "only the aggregate number of private tests passed", but `submit`
prints per-test verdicts; and the `strip()` comparison makes the E02 test
`'   spaces   '` unable to detect a trimming echo.

`esoverified probes --target hardened` runs the same exploits, plus a ninth (rewriting the
client to talk to a fake grader), against esoverified's harness, where a separate grader
process owns the tests, the state and every limit. **All 9 are blocked.**

## 4. The official interpreters deviate from their language specs

esoverified's fast interpreters (merged instruction runs, one-step "simple loops",
exact step accounting) agree with the official interpreters on **9,000 fuzzed programs**
(3,000 per language: output, success and error kind), including the exact step at which
`StepLimitExceeded` fires. Their `spec` dialect differs from the official one in these
documented places:

| Language | Official interpreter | Language spec / reference | Consequence |
|---|---|---|---|
| Whitespace | `div` is `int(a / b)`: float division, truncating | exact floored `div` (Haskell reference) | wrong digits above 2^53 (e.g. `(2^60+3) div 10`), and `-7 div 2 = -3` instead of `-4` |
| Befunge-98 | `p` stores `chr(v % 256)`; fungespace is the program's bounding box | cells hold any integer; space is unbounded | storing 400 reads back 144 |
| Befunge-98 | `/` and `%` by zero raise an error | push 0 | programs that rely on the spec crash |
| Befunge-98 | `/` is float `int(a / b)`; `%` is Python's floored modulo | truncating `/` and `%` with matching signs | `a == (a / b) * b + a % b` fails for negatives |

None of this is a problem if agents only target the official interpreter, but a
Befunge program written from the spec (or from training data) can fail for reasons the
language card does not mention. Reproduce: `esoverified difftest`.

## 5. Reference programs in the target languages

The benchmark ships no reference solutions. esoc (see `DESIGN.md`) compiles one IR
program per problem to all three languages; an oracle is **verified** when it reproduces
every expected output on the official interpreter semantics within the official
10,000,000-step cap.

| Language | Official tests | Fresh suite (edges + 30 random) | Largest run |
|---|---|---|---|
| Whitespace | 80/80 | 80/80 | 0.4M steps |
| Befunge-98 | 80/80 | 80/80 | 7.1M steps |
| Brainfuck | 70/80 | 46/80 | 10M cap (array-heavy problems time out) |

Brainfuck is where a general compiler meets the tape: random access to element *i* moves a
counter across *i* records, so array-heavy problems on long inputs exceed the step cap
even though the program is correct. The Harbor exporter only emits a task when its oracle
passes that task's own tests within the cap.
