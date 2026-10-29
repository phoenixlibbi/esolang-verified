"""Brainfuck: 8-bit wrapping cells, tape unbounded to the right, EOF reads 0.

The official interpreter follows this common convention, so both dialects are the
same here. The value of this implementation is speed with *exact* step accounting:

* runs of the same instruction are merged (``+-`` runs freely; ``<`` and ``>`` runs
  are kept separate so a negative-pointer error is detected exactly);
* "simple" loops (body of only ``+-<>``, net pointer move 0, loop cell changing by
  exactly +1 or -1 per iteration) are executed in one go.

Every shortcut advances the step counter by exactly what the official interpreter
counts (it checks ``steps >= max_steps`` before each instruction), so programs hit
``StepLimitExceeded`` at the same point. ``tests/test_interp_diff.py`` checks this
against the vendored upstream interpreter on fuzzed programs.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .common import DEFAULT_MAX_STEPS, EsoError, InputBuffer, StepLimitExceeded

ADD, MOVE, OUT, IN, JZ, JNZ, LOOP = range(7)


def compile_ops(program: str) -> List[list]:
    raw = [c for c in program if c in "+-<>.,[]"]
    depth = 0
    for c in raw:
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth < 0:
                raise EsoError("SyntaxError", "Unmatched closing bracket ']'.")
    if depth:
        raise EsoError("SyntaxError", "Unmatched opening bracket '['.")

    ops: List[list] = []   # [code, arg, raw_len, ...]
    stack: List[int] = []
    i, n = 0, len(raw)
    while i < n:
        c = raw[i]
        if c in "+-":
            v, k = 0, 0
            while i < n and raw[i] in "+-":
                v += 1 if raw[i] == "+" else -1
                i += 1
                k += 1
            ops.append([ADD, v, k])
            continue
        if c in "<>":
            k = 0
            while i < n and raw[i] == c:
                i += 1
                k += 1
            ops.append([MOVE, k if c == ">" else -k, k])
            continue
        if c == ".":
            ops.append([OUT, 0, 1])
        elif c == ",":
            ops.append([IN, 0, 1])
        elif c == "[":
            stack.append(len(ops))
            ops.append([JZ, 0, 1])
        else:  # "]"
            j = stack.pop()
            ops.append([JNZ, j, 1])
            ops[j][1] = len(ops) - 1
            _mark_simple_loop(ops, j)
        i += 1
    return ops


def _mark_simple_loop(ops: List[list], j: int) -> None:
    body = ops[j + 1:-1]
    if not body or any(op[0] not in (ADD, MOVE) for op in body):
        return
    off = min_off = raw_len = 0
    deltas: Dict[int, int] = {}
    for op in body:
        raw_len += op[2]
        if op[0] == MOVE:
            off += op[1]
            min_off = min(min_off, off)
        else:
            deltas[off] = deltas.get(off, 0) + op[1]
    if off != 0 or deltas.get(0, 0) % 256 not in (1, 255):
        return
    effects = tuple((k, v) for k, v in deltas.items() if k != 0 and v % 256)
    # [LOOP, index_of_closing, 1, loop_delta, effects, min_offset, body_raw_len]
    ops[j] = [LOOP, ops[j][1], 1, deltas[0] % 256, effects, min_off, raw_len]


def execute(program: str, input_data: str = "", *, dialect: str = "official",
            max_steps: int = DEFAULT_MAX_STEPS) -> Tuple[str, int]:
    if dialect not in ("official", "spec"):
        raise ValueError(f"unknown dialect {dialect!r}")
    ops = compile_ops(program)
    tape: Dict[int, int] = {}
    get = tape.get
    ptr = ip = steps = 0
    out: List[str] = []
    ibuf = InputBuffer(input_data)
    nops = len(ops)
    while ip < nops:
        op = ops[ip]
        code = op[0]
        if code == ADD:
            steps += op[2]
            if steps > max_steps:
                raise StepLimitExceeded(max_steps)
            tape[ptr] = (get(ptr, 0) + op[1]) % 256
            ip += 1
        elif code == MOVE:
            if op[1] < 0 and ptr + op[1] < 0:
                # official executes '<' one by one: the step limit may come first
                if steps + ptr + 1 > max_steps:
                    raise StepLimitExceeded(max_steps)
                raise EsoError("RuntimeError", "Tape pointer moved to negative index.")
            steps += op[2]
            if steps > max_steps:
                raise StepLimitExceeded(max_steps)
            ptr += op[1]
            ip += 1
        elif code == LOOP:
            cell = get(ptr, 0)
            if cell == 0:
                steps += 1
                if steps > max_steps:
                    raise StepLimitExceeded(max_steps)
                ip = op[1] + 1
                continue
            if ptr + op[5] < 0:
                # the body would move the pointer below zero: run it the slow way
                ops_slow = op
                ip = _run_body_slow(ops, ip, ops_slow, tape, ptr, max_steps, steps)
                # _run_body_slow always raises; keep linters calm
                continue
            iters = cell if op[3] == 255 else 256 - cell
            steps += iters * (op[6] + 2)
            if steps > max_steps:
                raise StepLimitExceeded(max_steps)
            for k, v in op[4]:
                tape[ptr + k] = (get(ptr + k, 0) + v * iters) % 256
            tape[ptr] = 0
            ip = op[1] + 1
        elif code == JZ:
            steps += 1
            if steps > max_steps:
                raise StepLimitExceeded(max_steps)
            ip = op[1] + 1 if get(ptr, 0) == 0 else ip + 1
        elif code == JNZ:
            steps += 1
            if steps > max_steps:
                raise StepLimitExceeded(max_steps)
            ip = op[1] if get(ptr, 0) != 0 else ip + 1
        elif code == OUT:
            steps += 1
            if steps > max_steps:
                raise StepLimitExceeded(max_steps)
            out.append(chr(get(ptr, 0)))
            ip += 1
        else:  # IN
            steps += 1
            if steps > max_steps:
                raise StepLimitExceeded(max_steps)
            ch = ibuf.read_char()
            tape[ptr] = 0 if ch is None else ord(ch) % 256
            ip += 1
    return "".join(out), steps


def _run_body_slow(ops, ip, op, tape, ptr, max_steps, steps):
    """A simple loop whose body dips below cell 0: replay instruction by instruction
    until the official interpreter's error (negative pointer or step limit)."""
    end = op[1]
    get = tape.get
    while True:
        steps += 1  # '['
        if steps > max_steps:
            raise StepLimitExceeded(max_steps)
        if get(ptr, 0) == 0:  # pragma: no cover - entry guaranteed non-zero
            return end + 1
        for k in range(ip + 1, end):
            o = ops[k]
            if o[0] == ADD:
                steps += o[2]
                if steps > max_steps:
                    raise StepLimitExceeded(max_steps)
                tape[ptr] = (get(ptr, 0) + o[1]) % 256
            else:
                if o[1] < 0 and ptr + o[1] < 0:
                    if steps + ptr + 1 > max_steps:
                        raise StepLimitExceeded(max_steps)
                    raise EsoError("RuntimeError", "Tape pointer moved to negative index.")
                steps += o[2]
                if steps > max_steps:
                    raise StepLimitExceeded(max_steps)
                ptr += o[1]
        steps += 1  # ']'
        if steps > max_steps:
            raise StepLimitExceeded(max_steps)
        if get(ptr, 0) == 0:  # pragma: no cover - min_off < 0 guarantees an error first
            return end + 1
