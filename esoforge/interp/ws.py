"""Whitespace: a stack machine written in Space, Tab and Linefeed.

Dialects
--------
* ``official``: integer division is ``int(a / b)`` (float division, truncating),
  modulo is Python's ``%`` (floored): exactly what the paper's interpreter does.
  ``int(a / b)`` loses precision once |a| exceeds 2**53, and its truncation does not
  match the floored modulo, so ``(a / b) * b + a % b == a`` fails for negatives.
* ``spec``: exact floored division and modulo (the reference Haskell implementation
  uses ``div``/``mod``), and ``out_char`` prints any Unicode code point.

Step counting matches the official interpreter (labels count as a step when executed).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .common import DEFAULT_MAX_STEPS, EsoError, InputBuffer, StepLimitExceeded

S, T, L = " ", "\t", "\n"


def parse(program: str) -> List[Tuple[str, object]]:
    toks = [c for c in program if c in (S, T, L)]
    n = len(toks)
    i = 0
    instrs: List[Tuple[str, object]] = []

    def pop(purpose: str) -> str:
        nonlocal i
        if i >= n:
            raise EsoError("SyntaxError", f"Unexpected end while reading {purpose}.")
        c = toks[i]
        i += 1
        return c

    def number() -> int:
        sign = pop("number sign")
        bits = []
        while True:
            c = pop("number")
            if c == L:
                break
            bits.append("0" if c == S else "1")
        v = int("".join(bits), 2) if bits else 0
        return -v if sign == T else v

    def label() -> str:
        bits = []
        while True:
            c = pop("label")
            if c == L:
                break
            bits.append("S" if c == S else "T")
        return "".join(bits)

    while i < n:
        c1 = pop("IMP")
        if c1 == S:
            c2 = pop("stack manipulation")
            if c2 == S:
                instrs.append(("push", number()))
            elif c2 == L:
                c3 = pop("stack manipulation")
                instrs.append({S: ("dup", None), T: ("swap", None), L: ("discard", None)}[c3])
            else:  # T
                c3 = pop("stack manipulation")
                if c3 == S:
                    instrs.append(("copy", number()))
                elif c3 == L:
                    instrs.append(("slide", number()))
                else:
                    raise EsoError("SyntaxError", "Invalid stack instruction.")
        elif c1 == T:
            c2 = pop("tab-IMP")
            if c2 == S:
                key = pop("arithmetic") + pop("arithmetic")
                ops = {S + S: "add", S + T: "sub", S + L: "mul", T + S: "div", T + T: "mod"}
                if key not in ops:
                    raise EsoError("SyntaxError", "Invalid arithmetic instruction.")
                instrs.append((ops[key], None))
            elif c2 == T:
                c3 = pop("heap access")
                if c3 == L:
                    raise EsoError("SyntaxError", "Invalid heap instruction.")
                instrs.append(("store" if c3 == S else "retrieve", None))
            else:  # L
                key = pop("io") + pop("io")
                ops = {S + S: "out_char", S + T: "out_num", T + S: "read_char", T + T: "read_num"}
                if key not in ops:
                    raise EsoError("SyntaxError", "Invalid IO instruction.")
                instrs.append((ops[key], None))
        else:  # L
            c2 = pop("flow control")
            if c2 == S:
                c3 = pop("flow control")
                instrs.append(({S: "label", T: "call", L: "jump"}[c3], label()))
            elif c2 == T:
                c3 = pop("flow control")
                if c3 == L:
                    instrs.append(("ret", None))
                else:
                    instrs.append(("jz" if c3 == S else "jn", label()))
            else:
                c3 = pop("flow control")
                if c3 != L:
                    raise EsoError("SyntaxError", "Invalid flow instruction.")
                instrs.append(("end", None))
    return instrs


def execute(program: str, input_data: str = "", *, dialect: str = "official",
            max_steps: int = DEFAULT_MAX_STEPS) -> Tuple[str, int]:
    if dialect not in ("official", "spec"):
        raise ValueError(f"unknown dialect {dialect!r}")
    spec = dialect == "spec"
    instrs = parse(program)
    labels: Dict[str, int] = {}
    for idx, (op, arg) in enumerate(instrs):
        if op == "label":
            if arg in labels:
                raise EsoError("SyntaxError", f"Duplicate label '{arg}'.")
            labels[arg] = idx  # type: ignore[index]
    stack: List[int] = []
    heap: Dict[int, int] = {}
    calls: List[int] = []
    out: List[str] = []
    ibuf = InputBuffer(input_data)
    ip = steps = 0
    n = len(instrs)

    def pop() -> int:
        if not stack:
            raise EsoError("StackUnderflow", "Stack underflow.")
        return stack.pop()

    def target(lbl: object) -> int:
        if lbl not in labels:
            raise EsoError("RuntimeError", f"Unknown label '{lbl}'.")
        return labels[lbl]  # type: ignore[index]

    while ip < n:
        if steps >= max_steps:
            raise StepLimitExceeded(max_steps)
        steps += 1
        op, arg = instrs[ip]
        if op == "push":
            stack.append(arg)  # type: ignore[arg-type]
        elif op == "dup":
            if not stack:
                raise EsoError("StackUnderflow", "Cannot duplicate from empty stack.")
            stack.append(stack[-1])
        elif op == "swap":
            if len(stack) < 2:
                raise EsoError("StackUnderflow", "Swap requires two stack values.")
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif op == "discard":
            pop()
        elif op == "copy":
            k = int(arg)  # type: ignore[arg-type]
            if k < 0 or k >= len(stack):
                raise EsoError("RuntimeError", "Copy index out of range.")
            stack.append(stack[-1 - k])
        elif op == "slide":
            k = int(arg)  # type: ignore[arg-type]
            if k < 0:
                raise EsoError("RuntimeError", "Slide count cannot be negative.")
            if len(stack) < k + 1:
                raise EsoError("StackUnderflow", "Slide requires more stack values.")
            top = stack.pop()
            if k:
                del stack[-k:]
            stack.append(top)
        elif op in ("add", "sub", "mul", "div", "mod"):
            b = pop()
            a = pop()
            if op == "add":
                stack.append(a + b)
            elif op == "sub":
                stack.append(a - b)
            elif op == "mul":
                stack.append(a * b)
            elif op == "div":
                if b == 0:
                    raise EsoError("DivisionByZero", "Division by zero.")
                stack.append(a // b if spec else int(a / b))
            else:
                if b == 0:
                    raise EsoError("DivisionByZero", "Modulo by zero.")
                stack.append(a % b)
        elif op == "store":
            v = pop()
            heap[pop()] = v
        elif op == "retrieve":
            stack.append(heap.get(pop(), 0))
        elif op == "out_char":
            v = pop()
            out.append(chr(v) if spec and 0 <= v < 0x110000 else chr(v % 256))
        elif op == "out_num":
            out.append(str(pop()))
        elif op == "read_char":
            addr = pop()
            ch = ibuf.read_char()
            heap[addr] = -1 if ch is None else ord(ch)
        elif op == "read_num":
            addr = pop()
            v: Optional[int] = ibuf.read_int()
            heap[addr] = -1 if v is None else v
        elif op == "label":
            pass
        elif op == "call":
            calls.append(ip + 1)
            ip = target(arg)
            continue
        elif op == "jump":
            ip = target(arg)
            continue
        elif op == "jz":
            if pop() == 0:
                ip = target(arg)
                continue
        elif op == "jn":
            if pop() < 0:
                ip = target(arg)
                continue
        elif op == "ret":
            if not calls:
                raise EsoError("RuntimeError", "Return with empty call stack.")
            ip = calls.pop()
            continue
        elif op == "end":
            break
        ip += 1
    return "".join(out), steps
