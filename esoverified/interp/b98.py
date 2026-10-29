"""Befunge-98 (core instruction set used by EsoLang-Bench).

Dialects
--------
* ``official``: reproduces the paper's interpreter, including its deviations from the
  Funge-98 specification:

  - fungespace is the program's bounding box, and coordinates wrap modulo its size;
  - ``p`` stores ``chr(v % 256)``, so a cell holds only a byte (``g`` returns 0..255);
  - ``/`` is ``int(a / b)`` (float division) and ``%`` is Python's floored modulo;
  - division or modulo by zero is an error.

* ``spec``: Funge-98 storage and arithmetic: unbounded fungespace whose cells hold any
  integer, exact truncating ``/`` and ``%`` with the sign of the dividend, and division
  or modulo by zero pushes 0. I/O keeps the benchmark's conventions (``~`` pushes -1 at
  EOF, ``&`` without a number is an error) so the two dialects differ only in storage
  and arithmetic.

Step counting matches the official interpreter: every visited cell, including spaces,
is one step.
"""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

from .common import DEFAULT_MAX_STEPS, EsoError, InputBuffer, StepLimitExceeded


def _tdiv(a: int, b: int) -> int:
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def _tmod(a: int, b: int) -> int:
    return a - b * _tdiv(a, b)


def execute(program: str, input_data: str = "", *, dialect: str = "official",
            max_steps: int = DEFAULT_MAX_STEPS) -> Tuple[str, int]:
    if dialect not in ("official", "spec"):
        raise ValueError(f"unknown dialect {dialect!r}")
    spec = dialect == "spec"
    lines = program.splitlines() or [""]
    width = max(1, max(len(line) for line in lines))
    height = max(1, len(lines))
    grid: Dict[Tuple[int, int], int] = {}
    for y, line in enumerate(lines):
        for x, ch in enumerate(line):
            if ch != " ":
                grid[(x, y)] = ord(ch)
    # spec: bounding box of non-space cells (grows with p)
    minx, miny, maxx, maxy = 0, 0, width - 1, height - 1

    ibuf = InputBuffer(input_data)
    out: List[str] = []
    stack: List[int] = []
    x = y = 0
    dx, dy = 1, 0
    string_mode = False
    steps = 0

    def wrap(px: int, py: int) -> Tuple[int, int]:
        return px % width, py % height

    def cell(px: int, py: int) -> int:
        if not spec:
            px, py = px % width, py % height
        return grid.get((px, py), 32)

    def put(px: int, py: int, v: int) -> None:
        nonlocal minx, miny, maxx, maxy
        if not spec:
            px, py = px % width, py % height
            v = v % 256
            if v == 32:
                grid.pop((px, py), None)
            else:
                grid[(px, py)] = v
            return
        if v == 32:
            grid.pop((px, py), None)
        else:
            grid[(px, py)] = v
            minx, miny = min(minx, px), min(miny, py)
            maxx, maxy = max(maxx, px), max(maxy, py)

    def step_once() -> None:
        nonlocal x, y
        if not spec:
            x, y = (x + dx) % width, (y + dy) % height
            return
        nx, ny = x + dx, y + dy
        if minx <= nx <= maxx and miny <= ny <= maxy:
            x, y = nx, ny
            return
        # Lahey-space wrap: walk backwards to the far edge, then one step forward.
        bx, by = x, y
        while minx <= bx - dx <= maxx and miny <= by - dy <= maxy:
            bx, by = bx - dx, by - dy
        x, y = bx, by

    def move(count: int = 1) -> None:
        nonlocal dx, dy
        if count >= 0:
            for _ in range(count):
                step_once()
        else:
            dx, dy = -dx, -dy
            for _ in range(-count):
                step_once()
            dx, dy = -dx, -dy

    def pop() -> int:
        if not stack:
            raise EsoError("StackUnderflow", "Stack underflow.")
        return stack.pop()

    def binop(op: str, a: int, b: int) -> int:
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            if b == 0:
                if spec:
                    return 0
                raise EsoError("DivisionByZero", "Division by zero.")
            return _tdiv(a, b) if spec else int(a / b)
        if b == 0:
            if spec:
                return 0
            raise EsoError("DivisionByZero", "Modulo by zero.")
        return _tmod(a, b) if spec else a % b

    while True:
        if steps >= max_steps:
            raise StepLimitExceeded(max_steps)
        steps += 1
        c = cell(x, y)
        ch = chr(c) if 0 <= c < 0x110000 else "\0"
        if string_mode and ch != '"':
            stack.append(c)
            move()
            continue
        if ch.isdigit() and len(ch) == 1 and "0" <= ch <= "9":
            stack.append(c - 48)
        elif "a" <= ch <= "f":
            stack.append(c - 87)
        elif "A" <= ch <= "F":
            stack.append(c - 55)
        elif ch in "+-*/%":
            b = pop()
            a = pop()
            stack.append(binop(ch, a, b))
        elif ch == "!":
            stack.append(0 if pop() else 1)
        elif ch == "`":
            b = pop()
            a = pop()
            stack.append(1 if a > b else 0)
        elif ch == ":":
            stack.append(stack[-1] if stack else 0)
        elif ch == "\\":
            if len(stack) < 2:
                raise EsoError("StackUnderflow", "Swap needs two stack values.")
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif ch == "$":
            pop()
        elif ch == "n":
            stack.clear()
        elif ch == ">":
            dx, dy = 1, 0
        elif ch == "<":
            dx, dy = -1, 0
        elif ch == "^":
            dx, dy = 0, -1
        elif ch == "v":
            dx, dy = 0, 1
        elif ch == "?":
            dx, dy = random.choice([(1, 0), (-1, 0), (0, -1), (0, 1)])
        elif ch == "_":
            dx, dy = (1, 0) if pop() == 0 else (-1, 0)
        elif ch == "|":
            dx, dy = (0, 1) if pop() == 0 else (0, -1)
        elif ch == "[":
            dx, dy = dy, -dx
        elif ch == "]":
            dx, dy = -dy, dx
        elif ch == "r":
            dx, dy = -dx, -dy
        elif ch == "x":
            ndy = pop()
            ndx = pop()
            dx, dy = ndx, ndy
            if dx == 0 and dy == 0:
                raise EsoError("RuntimeError", "Direction vector cannot be (0, 0).")
        elif ch == "#":
            move()
        elif ch == "'":
            move()
            stack.append(cell(x, y))
        elif ch == '"':
            string_mode = not string_mode
        elif ch == ".":
            out.append(f"{pop()} ")
        elif ch == ",":
            v = pop()
            out.append(chr(v) if spec and 0 <= v < 0x110000 else chr(v % 256))
        elif ch == "&":
            v = ibuf.read_int()
            if v is None:
                raise EsoError("InputError", "Expected integer input for '&'.")
            stack.append(v)
        elif ch == "~":
            r = ibuf.read_char()
            stack.append(-1 if r is None else ord(r))
        elif ch == "g":
            yy = pop()
            xx = pop()
            stack.append(cell(xx, yy))
        elif ch == "p":
            yy = pop()
            xx = pop()
            put(xx, yy, pop())
        elif ch == "j":
            move(pop())
        elif ch == "k":
            # Mirrors the official interpreter's (non-standard) k: find the next
            # non-space cell, execute a subset of instructions on it n times inline.
            n = pop()
            tx, ty = wrap(x + dx, y + dy) if not spec else (x + dx, y + dy)
            limit = 0
            while cell(tx, ty) == 32:
                tx, ty = (wrap(tx + dx, ty + dy) if not spec else (tx + dx, ty + dy))
                limit += 1
                if limit > width * height:
                    raise EsoError("RuntimeError", "k: no non-space instruction found.")
            t = chr(cell(tx, ty)) if 0 <= cell(tx, ty) < 0x110000 else "\0"
            if n <= 0:
                move()
            else:
                halted = False
                for _ in range(n):
                    if steps >= max_steps:
                        raise StepLimitExceeded(max_steps)
                    steps += 1
                    if t in "@q":
                        halted = True
                        break
                    if "0" <= t <= "9":
                        stack.append(ord(t) - 48)
                    elif "a" <= t <= "f":
                        stack.append(ord(t) - 87)
                    elif "A" <= t <= "F":
                        stack.append(ord(t) - 55)
                    elif t in "+-*/%":
                        b = pop()
                        a = pop()
                        stack.append(binop(t, a, b))
                    elif t == "!":
                        stack.append(0 if pop() else 1)
                    elif t == "`":
                        b = pop()
                        a = pop()
                        stack.append(1 if a > b else 0)
                    elif t == ":":
                        stack.append(stack[-1] if stack else 0)
                    elif t == "\\":
                        if len(stack) < 2:
                            raise EsoError("StackUnderflow", "Swap needs two stack values.")
                        stack[-1], stack[-2] = stack[-2], stack[-1]
                    elif t == "$":
                        pop()
                    elif t == "n":
                        stack.clear()
                    elif t == ".":
                        out.append(f"{pop()} ")
                    elif t == ",":
                        v = pop()
                        out.append(chr(v) if spec and 0 <= v < 0x110000 else chr(v % 256))
                    elif t == "&":
                        v = ibuf.read_int()
                        if v is None:
                            raise EsoError("InputError", "Expected integer input for '&'.")
                        stack.append(v)
                    elif t == "~":
                        r = ibuf.read_char()
                        stack.append(-1 if r is None else ord(r))
                    elif t == '"':
                        string_mode = not string_mode
                    elif t == ">":
                        dx, dy = 1, 0
                    elif t == "<":
                        dx, dy = -1, 0
                    elif t == "^":
                        dx, dy = 0, -1
                    elif t == "v":
                        dx, dy = 0, 1
                    elif t == "#":
                        move()
                    elif t == "r":
                        dx, dy = -dx, -dy
                    elif t == "[":
                        dx, dy = dy, -dx
                    elif t == "]":
                        dx, dy = -dy, dx
                    # anything else (including "'") is skipped, as upstream does
                if halted:
                    break
                move()
        elif ch == "s":
            v = pop()
            move()
            put(x, y, v)
        elif ch == ";":
            move()
            limit = 0
            while cell(x, y) != 59:
                move()
                limit += 1
                if limit > width * height:
                    raise EsoError("SyntaxError", "Comment opener ';' has no matching ';'.")
        elif ch in "@q":
            break
        elif ch == " ":
            pass
        else:
            raise EsoError("UnsupportedInstruction", f"Instruction '{ch}' is not supported.")
        move()
    return "".join(out), steps
