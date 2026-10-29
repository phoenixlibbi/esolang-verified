"""Whitespace interpreter with structured line/column errors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from esolang_common import EsolangError, InputBuffer, SourcePos


@dataclass(frozen=True)
class WSToken:
    char: str
    pos: SourcePos


@dataclass(frozen=True)
class WSInstruction:
    op: str
    arg: Optional[object]
    pos: SourcePos


class _WSTokenStream:
    def __init__(self, tokens: Sequence[WSToken], err_fn):
        self.tokens = tokens
        self.i = 0
        self.err_fn = err_fn

    def eof(self) -> bool:
        return self.i >= len(self.tokens)

    def pop(self, purpose: str = "token") -> WSToken:
        if self.i >= len(self.tokens):
            pos = self.tokens[-1].pos if self.tokens else SourcePos(1, 1)
            raise self.err_fn("SyntaxError", f"Unexpected end while reading {purpose}.", pos)
        tok = self.tokens[self.i]
        self.i += 1
        return tok


class WhitespaceInterpreter:
    LANGUAGE = "Whitespace"

    S = " "
    T = "\t"
    L = "\n"

    def __init__(self, max_steps: int = 1_000_000) -> None:
        self.max_steps = max_steps

    def _err(self, error_type: str, message: str, pos: Optional[SourcePos]) -> EsolangError:
        return EsolangError(
            self.LANGUAGE,
            error_type,
            message,
            line=pos.line if pos else None,
            column=pos.column if pos else None,
        )

    def _tokenize(self, program: str) -> List[WSToken]:
        tokens: List[WSToken] = []
        line = 1
        col = 1
        for ch in program:
            if ch in {self.S, self.T, self.L}:
                tokens.append(WSToken(ch, SourcePos(line, col)))
            if ch == "\n":
                line += 1
                col = 1
            else:
                col += 1
        return tokens

    def _read_number(self, ts: _WSTokenStream, start_pos: SourcePos) -> int:
        sign_tok = ts.pop("number sign")
        if sign_tok.char not in {self.S, self.T}:
            raise self._err("SyntaxError", "Number sign must be Space or Tab.", sign_tok.pos)

        bits: List[str] = []
        while True:
            tok = ts.pop("number")
            if tok.char == self.L:
                break
            if tok.char not in {self.S, self.T}:
                raise self._err("SyntaxError", "Invalid bit in number.", tok.pos)
            bits.append("0" if tok.char == self.S else "1")

        value = int("".join(bits), 2) if bits else 0
        if sign_tok.char == self.T:
            value = -value
        return value

    def _read_label(self, ts: _WSTokenStream, start_pos: SourcePos) -> str:
        bits: List[str] = []
        while True:
            tok = ts.pop("label")
            if tok.char == self.L:
                break
            if tok.char not in {self.S, self.T}:
                raise self._err("SyntaxError", "Invalid bit in label.", tok.pos)
            bits.append("S" if tok.char == self.S else "T")
        return "".join(bits)

    def _parse(self, tokens: Sequence[WSToken]) -> List[WSInstruction]:
        ts = _WSTokenStream(tokens, self._err)
        instrs: List[WSInstruction] = []

        while not ts.eof():
            first = ts.pop("IMP")
            c1 = first.char

            if c1 == self.S:
                c2 = ts.pop("stack manipulation").char
                if c2 == self.S:
                    n = self._read_number(ts, first.pos)
                    instrs.append(WSInstruction("push", n, first.pos))
                elif c2 == self.L:
                    c3 = ts.pop("stack manipulation").char
                    if c3 == self.S:
                        instrs.append(WSInstruction("dup", None, first.pos))
                    elif c3 == self.T:
                        instrs.append(WSInstruction("swap", None, first.pos))
                    elif c3 == self.L:
                        instrs.append(WSInstruction("discard", None, first.pos))
                    else:
                        raise self._err("SyntaxError", "Invalid stack instruction.", first.pos)
                elif c2 == self.T:
                    c3 = ts.pop("stack manipulation").char
                    if c3 == self.S:
                        n = self._read_number(ts, first.pos)
                        instrs.append(WSInstruction("copy", n, first.pos))
                    elif c3 == self.L:
                        n = self._read_number(ts, first.pos)
                        instrs.append(WSInstruction("slide", n, first.pos))
                    else:
                        raise self._err("SyntaxError", "Invalid stack instruction.", first.pos)
                else:
                    raise self._err("SyntaxError", "Invalid stack instruction.", first.pos)

            elif c1 == self.T:
                c2 = ts.pop("tab-IMP").char
                if c2 == self.S:
                    c3 = ts.pop("arithmetic").char
                    c4 = ts.pop("arithmetic").char
                    if c3 == self.S and c4 == self.S:
                        instrs.append(WSInstruction("add", None, first.pos))
                    elif c3 == self.S and c4 == self.T:
                        instrs.append(WSInstruction("sub", None, first.pos))
                    elif c3 == self.S and c4 == self.L:
                        instrs.append(WSInstruction("mul", None, first.pos))
                    elif c3 == self.T and c4 == self.S:
                        instrs.append(WSInstruction("div", None, first.pos))
                    elif c3 == self.T and c4 == self.T:
                        instrs.append(WSInstruction("mod", None, first.pos))
                    else:
                        raise self._err("SyntaxError", "Invalid arithmetic instruction.", first.pos)
                elif c2 == self.T:
                    c3 = ts.pop("heap access").char
                    if c3 == self.S:
                        instrs.append(WSInstruction("store", None, first.pos))
                    elif c3 == self.T:
                        instrs.append(WSInstruction("retrieve", None, first.pos))
                    else:
                        raise self._err("SyntaxError", "Invalid heap instruction.", first.pos)
                elif c2 == self.L:
                    c3 = ts.pop("io").char
                    c4 = ts.pop("io").char
                    if c3 == self.S and c4 == self.S:
                        instrs.append(WSInstruction("out_char", None, first.pos))
                    elif c3 == self.S and c4 == self.T:
                        instrs.append(WSInstruction("out_num", None, first.pos))
                    elif c3 == self.T and c4 == self.S:
                        instrs.append(WSInstruction("read_char", None, first.pos))
                    elif c3 == self.T and c4 == self.T:
                        instrs.append(WSInstruction("read_num", None, first.pos))
                    else:
                        raise self._err("SyntaxError", "Invalid IO instruction.", first.pos)
                else:
                    raise self._err("SyntaxError", "Invalid Tab instruction.", first.pos)

            elif c1 == self.L:
                c2 = ts.pop("flow control").char
                if c2 == self.S:
                    c3 = ts.pop("flow control").char
                    if c3 == self.S:
                        label = self._read_label(ts, first.pos)
                        instrs.append(WSInstruction("label", label, first.pos))
                    elif c3 == self.T:
                        label = self._read_label(ts, first.pos)
                        instrs.append(WSInstruction("call", label, first.pos))
                    elif c3 == self.L:
                        label = self._read_label(ts, first.pos)
                        instrs.append(WSInstruction("jump", label, first.pos))
                    else:
                        raise self._err("SyntaxError", "Invalid flow instruction.", first.pos)
                elif c2 == self.T:
                    c3 = ts.pop("flow control").char
                    if c3 == self.S:
                        label = self._read_label(ts, first.pos)
                        instrs.append(WSInstruction("jz", label, first.pos))
                    elif c3 == self.T:
                        label = self._read_label(ts, first.pos)
                        instrs.append(WSInstruction("jn", label, first.pos))
                    elif c3 == self.L:
                        instrs.append(WSInstruction("ret", None, first.pos))
                    else:
                        raise self._err("SyntaxError", "Invalid flow instruction.", first.pos)
                elif c2 == self.L:
                    c3 = ts.pop("flow control").char
                    if c3 == self.L:
                        instrs.append(WSInstruction("end", None, first.pos))
                    else:
                        raise self._err("SyntaxError", "Invalid flow instruction.", first.pos)
                else:
                    raise self._err("SyntaxError", "Invalid flow instruction.", first.pos)
            else:
                raise self._err("SyntaxError", "Invalid instruction prefix.", first.pos)

        return instrs

    def run(self, program: str, input_data: str = "") -> str:
        tokens = self._tokenize(program)
        instrs = self._parse(tokens)

        labels: Dict[str, int] = {}
        for idx, ins in enumerate(instrs):
            if ins.op == "label":
                label = str(ins.arg)
                if label in labels:
                    raise self._err("SyntaxError", f"Duplicate label '{label}'.", ins.pos)
                labels[label] = idx

        stack: List[int] = []
        heap: Dict[int, int] = {}
        call_stack: List[int] = []
        output: List[str] = []
        ibuf = InputBuffer(input_data)

        def pop_stack(ins: WSInstruction) -> int:
            if not stack:
                raise self._err("StackUnderflow", "Stack underflow.", ins.pos)
            return stack.pop()

        ip = 0
        steps = 0
        while ip < len(instrs):
            if steps >= self.max_steps:
                raise self._err("StepLimitExceeded", f"Execution exceeded {self.max_steps} steps.", instrs[ip].pos)
            steps += 1

            ins = instrs[ip]
            op = ins.op

            if op == "push":
                stack.append(int(ins.arg))
            elif op == "dup":
                if not stack:
                    raise self._err("StackUnderflow", "Cannot duplicate from empty stack.", ins.pos)
                stack.append(stack[-1])
            elif op == "swap":
                if len(stack) < 2:
                    raise self._err("StackUnderflow", "Swap requires two stack values.", ins.pos)
                stack[-1], stack[-2] = stack[-2], stack[-1]
            elif op == "discard":
                pop_stack(ins)
            elif op == "copy":
                n = int(ins.arg)
                if n < 0 or n >= len(stack):
                    raise self._err("RuntimeError", "Copy index out of range.", ins.pos)
                stack.append(stack[-1 - n])
            elif op == "slide":
                n = int(ins.arg)
                if n < 0:
                    raise self._err("RuntimeError", "Slide count cannot be negative.", ins.pos)
                if len(stack) < n + 1:
                    raise self._err("StackUnderflow", "Slide requires more stack values.", ins.pos)
                top = stack.pop()
                del stack[-n:]
                stack.append(top)
            elif op in {"add", "sub", "mul", "div", "mod"}:
                b = pop_stack(ins)
                a = pop_stack(ins)
                if op == "add":
                    stack.append(a + b)
                elif op == "sub":
                    stack.append(a - b)
                elif op == "mul":
                    stack.append(a * b)
                elif op == "div":
                    if b == 0:
                        raise self._err("DivisionByZero", "Division by zero.", ins.pos)
                    stack.append(int(a / b))
                elif op == "mod":
                    if b == 0:
                        raise self._err("DivisionByZero", "Modulo by zero.", ins.pos)
                    stack.append(a % b)
            elif op == "store":
                value = pop_stack(ins)
                addr = pop_stack(ins)
                heap[addr] = value
            elif op == "retrieve":
                addr = pop_stack(ins)
                stack.append(heap.get(addr, 0))
            elif op == "out_char":
                output.append(chr(pop_stack(ins) % 256))
            elif op == "out_num":
                output.append(str(pop_stack(ins)))
            elif op == "read_char":
                addr = pop_stack(ins)
                ch = ibuf.read_char()
                if ch is None:
                    heap[addr] = -1  # EOF sentinel
                else:
                    heap[addr] = ord(ch)
            elif op == "read_num":
                addr = pop_stack(ins)
                n = ibuf.read_int()
                if n is None:
                    heap[addr] = -1  # EOF sentinel
                else:
                    heap[addr] = n
            elif op == "label":
                pass
            elif op == "call":
                label = str(ins.arg)
                if label not in labels:
                    raise self._err("RuntimeError", f"Unknown label '{label}'.", ins.pos)
                call_stack.append(ip + 1)
                ip = labels[label]
                continue
            elif op == "jump":
                label = str(ins.arg)
                if label not in labels:
                    raise self._err("RuntimeError", f"Unknown label '{label}'.", ins.pos)
                ip = labels[label]
                continue
            elif op == "jz":
                label = str(ins.arg)
                value = pop_stack(ins)
                if value == 0:
                    if label not in labels:
                        raise self._err("RuntimeError", f"Unknown label '{label}'.", ins.pos)
                    ip = labels[label]
                    continue
            elif op == "jn":
                label = str(ins.arg)
                value = pop_stack(ins)
                if value < 0:
                    if label not in labels:
                        raise self._err("RuntimeError", f"Unknown label '{label}'.", ins.pos)
                    ip = labels[label]
                    continue
            elif op == "ret":
                if not call_stack:
                    raise self._err("RuntimeError", "Return with empty call stack.", ins.pos)
                ip = call_stack.pop()
                continue
            elif op == "end":
                break
            else:
                raise self._err("RuntimeError", f"Unhandled instruction '{op}'.", ins.pos)

            ip += 1

        return "".join(output)
