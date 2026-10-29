> **Start solving now.** The session is initialized. Begin by fetching your first problem:
> ```
> python harness.py fetch
> ```
> Work through all 80 problems sequentially. For each problem: read the description, generate your own test cases, use `run` to test, then `submit` when confident. Do NOT skip without attempting — see skip policy below.

# EsoLang-Bench: Brainfuck

You are solving 80 brainfuck programming problems sequentially.
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

## Brainfuck Language Reference

### Commands

| Cmd | Description |
|-----|-------------|
| `>` | Move pointer right |
| `<` | Move pointer left |
| `+` | Increment cell (wraps 255->0) |
| `-` | Decrement cell (wraps 0->255) |
| `.` | Output cell as ASCII character |
| `,` | Read one byte into cell (0 if EOF) |
| `[` | Jump past matching `]` if cell is 0 |
| `]` | Jump back to matching `[` if cell nonzero |

All other characters are comments.

### Memory Model

- Unbounded tape of unsigned byte cells (0-255), initialized to 0.
- Pointer starts at cell 0; cannot go below 0 (runtime error).

### Essential Patterns

- **Zero a cell:** `[-]`
- **Move (destructive):** `[->+<]` (cell 0 to cell 1)
- **Copy:** `[->+>+<<]>>[-<<+>>]` (cell 0 to cell 1, using cell 2 as temp)
- **Add cell 1 into cell 0:** `>[-<+>]<`
- **Subtract cell 1 from cell 0:** `>[-<->]<`
- **Read loop:** `,[...,]` reads until EOF (0)
- **Print decimal number:** Divide by 10 repeatedly, store remainders, print in reverse + ASCII 48

### ASCII Quick Reference

`0`=48, `9`=57, `A`=65, `Z`=90, `a`=97, `z`=122, space=32, newline=10, `-`=45

### Common Pitfalls

- **Number I/O**: Input arrives as ASCII chars ('5'=53), not raw numbers. Output must also be ASCII digits. This is the #1 error source.
- **Forgetting to zero cells** before reuse.
- **Cell overflow**: 255+1=0, 0-1=255. Can cause infinite loops.
- **Pointer tracking**: Always keep a written map of which cell holds what.
- **Multi-digit numbers**: Parsing and printing require digit-by-digit handling.
