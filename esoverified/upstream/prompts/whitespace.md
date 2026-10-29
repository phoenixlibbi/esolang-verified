> **Start solving now.** The session is initialized. Begin by fetching your first problem:
> ```
> python harness.py fetch
> ```
> Work through all 80 problems sequentially. For each problem: read the description, generate your own test cases, use `run` to test, then `submit` when confident. Do NOT skip without attempting — see skip policy below.

# EsoLang-Bench: Whitespace

You are solving 80 whitespace programming problems sequentially.
Problems span 4 difficulty tiers: E01-E20 (easy), M01-M20 (medium), H01-H20 (hard), X01-X20 (extra-hard).

Each problem has 6 hidden test cases you cannot see. No test cases are provided -- generate your own test inputs from the problem descriptions.

## Harness Commands

```bash
python harness.py fetch                          # Get next problem
python harness.py run <code_file> --input "..."  # Test with custom input (unlimited)
python harness.py submit <problem_id> <file>     # Hidden evaluation (max 3 per problem)
python harness.py status                         # Progress dashboard
python harness.py skip                           # Skip ONLY after attempting (see policy)
```

## Rules

- Solve problems in order. `fetch` advances to the next.
- Maximum 3 submissions per problem. Use `run` (unlimited) to test first.
- `submit` returns PASS/WRONG ANSWER/RUNTIME ERROR per hidden test -- no inputs or expected outputs shown.
- Problem is solved only if 6/6 hidden tests pass.
- Do not read private test files, reverse-engineer the harness, or hardcode outputs.

## CRITICAL: No Skipping — Use All 3 Submissions

- You MUST work on every problem until you either score 6/6 OR use all 3 submissions. Do NOT move to the next problem with unused submissions remaining.
- You CANNOT revisit problems later — once you move on, the problem is gone forever. Every unused submission is wasted.
- There is NO time limit. You have UNLIMITED time and UNLIMITED test runs (`run` command). The ONLY limit is 3 submissions per problem.
- For each problem: read the description, write a genuine solution, test it thoroughly with `run` using multiple inputs until it produces correct output, THEN submit.
- Do NOT submit untested code. Do NOT submit placeholder or stub solutions. Every submission must be a genuine, tested attempt.
- If a submission returns WRONG ANSWER or RUNTIME ERROR: analyze the failure, try a completely different approach, test it, then use your next submission.
- Even if a problem seems extremely difficult, you must use all 3 submissions with genuinely different approaches before moving on. A partial score (1-5/6) is far better than 0/6.
- Do NOT call `fetch` or `skip` to move to the next problem while you still have submissions remaining on the current one.


## Scoring

- Per problem: tests passed / 6
- Overall: problems solved / 80 and total tests passed / 480

## Whitespace Language Reference

### Encoding

Programs use only: Space (S, ASCII 32), Tab (T, ASCII 9), Linefeed (L, ASCII 10). All other chars are ignored.

### Instruction Encoding (selected)

```
Stack:    SS<num>  push number; SLS dup; SLT swap; SLL discard
Arith:    TSSS add; TSST sub; TSSL mul; TSTS div; TSTT mod
Heap:     TTS store; TTT retrieve
I/O:      TLSS out_char; TLST out_num; TLTS read_char; TLTT read_num
Flow:     LSS<lbl> label; LST<lbl> call; LSL<lbl> jump;
          LTS<lbl> jz; LTT<lbl> jn (jump if negative);
          LTL ret; LLL end
```

### Key Concepts

- **Number encoding**: Sign bit (S=+, T=-) + binary digits (S=0, T=1) + L terminator.
- **Heap-based I/O**: `read_char`/`read_num` store to heap at a popped address, not the stack. Push address first, then read, then push address + retrieve to get value onto stack.
- **Labels**: Sequences of S and T terminated by L. Must be unique.

### Common Pitfalls

- **Heap I/O**: Read operations store to heap, not stack. Must retrieve afterward.
- **Sign bit required** even for positive numbers.
- **Always include the end instruction (LLL)** or execution runs off the end.
- **Stack order**: `sub` pops b then a, computes a-b.
