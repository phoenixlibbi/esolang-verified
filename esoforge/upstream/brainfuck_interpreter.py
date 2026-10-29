"""Brainfuck interpreter with structured line/column errors."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from esolang_common import EsolangError, InputBuffer, SourcePos


class BrainfuckInterpreter:
    LANGUAGE = "Brainfuck"

    def __init__(self, max_steps: int = 10_000_000) -> None:
        self.max_steps = max_steps

    def _err(self, error_type: str, message: str, pos: Optional[SourcePos]) -> EsolangError:
        return EsolangError(
            self.LANGUAGE,
            error_type,
            message,
            line=pos.line if pos else None,
            column=pos.column if pos else None,
        )

    def _parse(self, program: str) -> Tuple[List[Tuple[str, SourcePos]], Dict[int, int]]:
        instructions: List[Tuple[str, SourcePos]] = []
        line = 1
        col = 1
        bracket_stack: List[int] = []
        bracket_map: Dict[int, int] = {}
        for ch in program:
            if ch in "><+-.,[]":
                pos = SourcePos(line, col)
                idx = len(instructions)
                instructions.append((ch, pos))
                if ch == "[":
                    bracket_stack.append(idx)
                elif ch == "]":
                    if not bracket_stack:
                        raise self._err("SyntaxError", "Unmatched closing bracket ']'.", pos)
                    open_idx = bracket_stack.pop()
                    bracket_map[open_idx] = idx
                    bracket_map[idx] = open_idx
            if ch == "\n":
                line += 1
                col = 1
            else:
                col += 1

        if bracket_stack:
            idx = bracket_stack[-1]
            _, pos = instructions[idx]
            raise self._err("SyntaxError", "Unmatched opening bracket '['.", pos)
        return instructions, bracket_map

    def run(self, program: str, input_data: str = "") -> str:
        instructions, bracket_map = self._parse(program)
        tape: Dict[int, int] = {0: 0}
        ptr = 0
        ip = 0
        steps = 0
        output: List[str] = []
        ibuf = InputBuffer(input_data)

        while ip < len(instructions):
            if steps >= self.max_steps:
                _, pos = instructions[ip]
                raise self._err("StepLimitExceeded", f"Execution exceeded {self.max_steps} steps.", pos)
            steps += 1

            op, pos = instructions[ip]
            cell = tape.get(ptr, 0)
            if op == ">":
                ptr += 1
                tape.setdefault(ptr, 0)
                ip += 1
            elif op == "<":
                ptr -= 1
                if ptr < 0:
                    raise self._err("RuntimeError", "Tape pointer moved to negative index.", pos)
                tape.setdefault(ptr, 0)
                ip += 1
            elif op == "+":
                tape[ptr] = (cell + 1) % 256
                ip += 1
            elif op == "-":
                tape[ptr] = (cell - 1) % 256
                ip += 1
            elif op == ".":
                output.append(chr(cell))
                ip += 1
            elif op == ",":
                ch = ibuf.read_char()
                tape[ptr] = 0 if ch is None else ord(ch) % 256
                ip += 1
            elif op == "[":
                if cell == 0:
                    ip = bracket_map[ip] + 1
                else:
                    ip += 1
            elif op == "]":
                if cell != 0:
                    ip = bracket_map[ip]
                else:
                    ip += 1
        return "".join(output)
