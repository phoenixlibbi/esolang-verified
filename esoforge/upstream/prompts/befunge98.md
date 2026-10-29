> **Start solving now.** The session is initialized. Begin by fetching your first problem:
> ```
> python harness.py fetch
> ```
> Work through all 80 problems sequentially. For each problem: read the description, generate your own test cases, use `run` to test, then `submit` when confident. Do NOT skip without attempting — see skip policy below.

# EsoLang-Bench: Befunge-98

You are solving 80 befunge-98 programming problems sequentially.
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

## Befunge-98 Language Reference

### Program Structure

2D grid. Instruction pointer starts at (0,0) moving right. Wraps at edges. Ends at `@`.

### Instructions

**Stack:** `0-9` push digit; `a-f` push 10-15; `"` toggle string mode; `:` dup; `\` swap; `$` pop; `n` clear stack
**Arithmetic:** `+` `-` `*` `/` `%` (pop b, pop a, push a op b)
**Comparison:** `!` (NOT); `` ` `` (greater-than)
**Direction:** `>` `<` `^` `v` `?`(random) `[`(turn left) `]`(turn right) `r`(reverse) `#`(skip next) `j`(jump n)
**Branch:** `_` (right if 0, left if nonzero); `|` (down if 0, up if nonzero)
**I/O:** `.` print int+space; `,` print char; `&` read int; `~` read char (-1 at EOF)
**Grid:** `g` get; `p` put; `s` store next; `'` fetch next
**Flow:** `@` end; `q` quit; `;` comment toggle; space=nop

### Essential Patterns

- **Print string:** `"!dlroW olleH">:#,_@` (push reversed, loop print)
- **Print loop:** `>:#,_@` (dup, skip print if 0, print char, repeat)
- **Read int:** `&` (built-in)
- **Conditional:** `!#v_` (branch on value)

### Common Pitfalls

- **`.` trailing space**: `.` outputs number + space. For clean output, convert to digit chars and use `,`.
- **Stack order**: `52-` = 5-2=3, not 2-5.
- **String mode**: `"abc"` pushes a,b,c in order; they pop as c,b,a.
- **Missing `@`**: IP wraps and re-executes, hitting step limit.
- **`~` returns -1 at EOF**, not 0.
