"""Befunge-98 (core instruction set) interpreter with structured errors."""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from esolang_common import EsolangError, InputBuffer, SourcePos


class Befunge98Interpreter:
    LANGUAGE = "Befunge-98"

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

    def run(self, program: str, input_data: str = "") -> str:
        lines = program.splitlines()
        if not lines:
            lines = [""]

        width = max(1, max(len(line) for line in lines))
        height = max(1, len(lines))

        grid: Dict[Tuple[int, int], str] = {}
        for y, line in enumerate(lines):
            for x, ch in enumerate(line):
                if ch != " ":
                    grid[(x, y)] = ch

        def norm(x: int, y: int) -> Tuple[int, int]:
            return (x % width, y % height)

        def get_char(x: int, y: int) -> str:
            x, y = norm(x, y)
            return grid.get((x, y), " ")

        def set_char(x: int, y: int, ch: str) -> None:
            x, y = norm(x, y)
            if ch == " ":
                grid.pop((x, y), None)
            else:
                grid[(x, y)] = ch

        def get_pos(x: int, y: int) -> SourcePos:
            x, y = norm(x, y)
            return SourcePos(y + 1, x + 1)

        ibuf = InputBuffer(input_data)
        output: List[str] = []
        stack: List[int] = []

        x = 0
        y = 0
        dx = 1
        dy = 0
        string_mode = False
        steps = 0

        def pop(pos: SourcePos) -> int:
            if not stack:
                raise self._err("StackUnderflow", "Stack underflow.", pos)
            return stack.pop()

        def move(count: int = 1) -> Tuple[int, int]:
            nonlocal x, y
            for _ in range(abs(count)):
                if count >= 0:
                    x += dx
                    y += dy
                else:
                    x -= dx
                    y -= dy
                x, y = norm(x, y)
            return x, y

        while True:
            if steps >= self.max_steps:
                raise self._err("StepLimitExceeded", f"Execution exceeded {self.max_steps} steps.", get_pos(x, y))
            steps += 1

            pos = get_pos(x, y)
            ch = get_char(x, y)

            if string_mode and ch != '"':
                stack.append(ord(ch))
                move()
                continue

            if ch.isdigit():
                stack.append(int(ch))
            elif "a" <= ch <= "f":
                stack.append(10 + ord(ch) - ord("a"))
            elif "A" <= ch <= "F":
                stack.append(10 + ord(ch) - ord("A"))
            elif ch == "+":
                b = pop(pos)
                a = pop(pos)
                stack.append(a + b)
            elif ch == "-":
                b = pop(pos)
                a = pop(pos)
                stack.append(a - b)
            elif ch == "*":
                b = pop(pos)
                a = pop(pos)
                stack.append(a * b)
            elif ch == "/":
                b = pop(pos)
                a = pop(pos)
                if b == 0:
                    raise self._err("DivisionByZero", "Division by zero.", pos)
                stack.append(int(a / b))
            elif ch == "%":
                b = pop(pos)
                a = pop(pos)
                if b == 0:
                    raise self._err("DivisionByZero", "Modulo by zero.", pos)
                stack.append(a % b)
            elif ch == "!":
                a = pop(pos)
                stack.append(0 if a else 1)
            elif ch == "`":
                b = pop(pos)
                a = pop(pos)
                stack.append(1 if a > b else 0)
            elif ch == ":":
                stack.append(stack[-1] if stack else 0)
            elif ch == "\\":
                if len(stack) < 2:
                    raise self._err("StackUnderflow", "Swap needs two stack values.", pos)
                stack[-1], stack[-2] = stack[-2], stack[-1]
            elif ch == "$":
                pop(pos)
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
                a = pop(pos)
                dx, dy = (1, 0) if a == 0 else (-1, 0)
            elif ch == "|":
                a = pop(pos)
                dx, dy = (0, 1) if a == 0 else (0, -1)
            elif ch == "[":
                dx, dy = dy, -dx
            elif ch == "]":
                dx, dy = -dy, dx
            elif ch == "r":
                dx, dy = -dx, -dy
            elif ch == "x":
                ndy = pop(pos)
                ndx = pop(pos)
                dx, dy = ndx, ndy
                if dx == 0 and dy == 0:
                    raise self._err("RuntimeError", "Direction vector cannot be (0, 0).", pos)
            elif ch == "#":
                move()
            elif ch == "'":
                move()
                stack.append(ord(get_char(x, y)))
            elif ch == '"':
                string_mode = not string_mode
            elif ch == ".":
                output.append(f"{pop(pos)} ")
            elif ch == ",":
                output.append(chr(pop(pos) % 256))
            elif ch == "&":
                n = ibuf.read_int()
                if n is None:
                    raise self._err("InputError", "Expected integer input for '&'.", pos)
                stack.append(n)
            elif ch == "~":
                c = ibuf.read_char()
                stack.append(-1 if c is None else ord(c))
            elif ch == "g":
                yy = pop(pos)
                xx = pop(pos)
                stack.append(ord(get_char(xx, yy)))
            elif ch == "p":
                yy = pop(pos)
                xx = pop(pos)
                vv = pop(pos)
                set_char(xx, yy, chr(vv % 256))
            elif ch == "j":
                count = pop(pos)
                move(count)
            elif ch == "k":
                n = pop(pos)
                # Look ahead to find the target instruction (skip spaces)
                tx, ty = x + dx, y + dy
                tx, ty = norm(tx, ty)
                limit = 0
                while get_char(tx, ty) == " ":
                    tx += dx
                    ty += dy
                    tx, ty = norm(tx, ty)
                    limit += 1
                    if limit > width * height:
                        raise self._err("RuntimeError", "k: no non-space instruction found.", pos)
                target_ch = get_char(tx, ty)
                if n <= 0:
                    # Skip the next cell without executing
                    move()
                else:
                    for _k_iter in range(n):
                        if steps >= self.max_steps:
                            raise self._err("StepLimitExceeded", f"Execution exceeded {self.max_steps} steps.", pos)
                        steps += 1
                        tpos = get_pos(tx, ty)
                        # Execute target instruction inline
                        if target_ch == "@" or target_ch == "q":
                            return "".join(output)
                        elif target_ch.isdigit():
                            stack.append(int(target_ch))
                        elif "a" <= target_ch <= "f":
                            stack.append(10 + ord(target_ch) - ord("a"))
                        elif "A" <= target_ch <= "F":
                            stack.append(10 + ord(target_ch) - ord("A"))
                        elif target_ch == "+":
                            b = pop(tpos); a = pop(tpos); stack.append(a + b)
                        elif target_ch == "-":
                            b = pop(tpos); a = pop(tpos); stack.append(a - b)
                        elif target_ch == "*":
                            b = pop(tpos); a = pop(tpos); stack.append(a * b)
                        elif target_ch == "/":
                            b = pop(tpos); a = pop(tpos)
                            if b == 0:
                                raise self._err("DivisionByZero", "Division by zero.", tpos)
                            stack.append(int(a / b))
                        elif target_ch == "%":
                            b = pop(tpos); a = pop(tpos)
                            if b == 0:
                                raise self._err("DivisionByZero", "Modulo by zero.", tpos)
                            stack.append(a % b)
                        elif target_ch == "!":
                            a = pop(tpos); stack.append(0 if a else 1)
                        elif target_ch == "`":
                            b = pop(tpos); a = pop(tpos); stack.append(1 if a > b else 0)
                        elif target_ch == ":":
                            stack.append(stack[-1] if stack else 0)
                        elif target_ch == "\\":
                            if len(stack) < 2:
                                raise self._err("StackUnderflow", "Swap needs two stack values.", tpos)
                            stack[-1], stack[-2] = stack[-2], stack[-1]
                        elif target_ch == "$":
                            pop(tpos)
                        elif target_ch == "n":
                            stack.clear()
                        elif target_ch == ".":
                            output.append(f"{pop(tpos)} ")
                        elif target_ch == ",":
                            output.append(chr(pop(tpos) % 256))
                        elif target_ch == "&":
                            nn = ibuf.read_int()
                            if nn is None:
                                raise self._err("InputError", "Expected integer input for '&'.", tpos)
                            stack.append(nn)
                        elif target_ch == "~":
                            c = ibuf.read_char()
                            stack.append(-1 if c is None else ord(c))
                        elif target_ch == "'":
                            pass  # fetch char is positional, skip for k
                        elif target_ch == '"':
                            string_mode = not string_mode
                        elif target_ch == ">":
                            dx, dy = 1, 0
                        elif target_ch == "<":
                            dx, dy = -1, 0
                        elif target_ch == "^":
                            dx, dy = 0, -1
                        elif target_ch == "v":
                            dx, dy = 0, 1
                        elif target_ch == "#":
                            move()
                        elif target_ch == "r":
                            dx, dy = -dx, -dy
                        elif target_ch == "[":
                            dx, dy = dy, -dx
                        elif target_ch == "]":
                            dx, dy = -dy, dx
                        else:
                            pass  # Unknown targets are reflected in Funge-98, but we just skip
                    # After k execution, advance past the target cell
                    move()
            elif ch == "s":
                vv = pop(pos)
                move()
                set_char(x, y, chr(vv % 256))
            elif ch == ";":
                move()
                limit = 0
                while get_char(x, y) != ";":
                    move()
                    limit += 1
                    if limit > width * height:
                        raise self._err("SyntaxError", "Comment opener ';' has no matching ';'.", pos)
            elif ch == "@":
                break
            elif ch == "q":
                break
            elif ch == " ":
                pass
            else:
                raise self._err("UnsupportedInstruction", f"Instruction '{ch}' is not supported.", pos)

            move()

        return "".join(output)
