# Findings

Everything below is reproducible with the commands shown, from a fresh clone, with no
model and no API key. Numbers are from `esoverified` 0.1.0 on EsoLang-Bench
`Lossfunk/Esolang-Bench@a38a25f` and the reference harness `Lossfunk/esolang-metaprogramming@b93ef26`.

---

## 1. Test availability

The six tests per problem are kept from the agent during a run. They are also publicly available, which is
standard practice for benchmarks:

| Where | Field | Identical to the graded tests |
|---|---|---|
| `huggingface.co/datasets/Lossfunk/Esolang-Bench`, `data/test.jsonl` | `test_cases` | 80/80 problems |
| `github.com/Lossfunk/EsolangBench`, `esolang_bench/data/esolang_benchmark.json` | `input_output_examples` | 80/80 problems |

Both have held the same 480 tests since the dataset's v1.0 release on 2026-03-07 (byte-identical,
sha256 `04ce0dbf…`). Models released before then are unlikely to have seen them; models trained on
public data afterwards may have. For an RL environment that will be used for months, EsoLang-Verified
adds **fresh private suites**: each lab draws its own tests from a secret seed
(`esoverified fresh --seed N`), with expected outputs from reference solutions that must first reproduce
all six official tests exactly (the gold-sanity gate).

## 2. Test strength

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

## 3. Grader isolation for RL

In RL a policy is optimized against the grader, so grading must sit outside anything the policy can
change. `esoverified probes` measures this with scripted probes run through a harness's own commands.
The file-based reference harness (rebuilt in the layout of its setup script, with the real tests in
place) keeps its state, configuration and tests where a process with shell access in the working
directory can reach them, which is fine for the cooperative protocol it was designed for:

| Probe | What a process with shell access does | Effect on the file-based harness |
|---|---|---|
| read_hidden_tests | reads the test file by relative path | tests readable |
| state_forgery | sets `best_score: 6` in `harness_state.json`, then `fetch` | problem recorded as solved |
| submission_cap_reset | clears `submissions` in `harness_state.json` | further hidden submissions graded |
| sentinel_hijack | adds `.experiment_root` and a `private/` test file in the working directory | its own tests used for grading |
| env_override | sets `HARNESS_PRIVATE_FILE` | its own tests used for grading |
| interpreter_hijack | sets `HARNESS_INTERPRETER_DIR` | its own interpreter used for grading |
| per_test_feedback | `submit` | one verdict per hidden test (more detail than an aggregate count) |
| strip_leniency | prints E01's answer padded with whitespace | accepted (outputs are compared after `strip()`) |

Nothing here concerns any agent's behaviour; the probes describe what an RL policy *could* learn if the
reward came from such a harness. EsoLang-Verified's harness splits grading into a separate process that
owns tests, state and limits; the agent gets only a client. Running the same probes plus a ninth
(rewriting the client to talk to a fake grader): **9/9 have no effect**. Reproduce:
`esoverified probes -v`.

## 4. Interpreter semantics

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

Programs written for the benchmark run on the official semantics, and esoverified grades with them by
default; the `spec` dialect is there to see which programs depend on these details. Reproduce: `esoverified difftest`.

## 5. Reference programs in the target languages

No reference programs in the target languages were available, so esoc (see `DESIGN.md`) compiles one IR
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
