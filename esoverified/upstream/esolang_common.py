"""Shared utilities for esolang interpreters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class SourcePos:
    line: int
    column: int


class EsolangError(Exception):
    def __init__(
        self,
        language: str,
        error_type: str,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.language = language
        self.error_type = error_type
        self.message = message
        self.line = line
        self.column = column

    def to_dict(self) -> Dict[str, object]:
        return {
            "language": self.language,
            "error_type": self.error_type,
            "message": self.message,
            "line": self.line,
            "column": self.column,
        }

    def __str__(self) -> str:
        where = ""
        if self.line is not None and self.column is not None:
            where = f" at line {self.line}, column {self.column}"
        return f"{self.language} {self.error_type}{where}: {self.message}"


class InputBuffer:
    def __init__(self, data: str) -> None:
        self.data = data
        self.index = 0

    def read_char(self) -> Optional[str]:
        if self.index >= len(self.data):
            return None
        ch = self.data[self.index]
        self.index += 1
        return ch

    def read_int(self) -> Optional[int]:
        n = len(self.data)
        while self.index < n and self.data[self.index].isspace():
            self.index += 1
        if self.index >= n:
            return None

        start = self.index
        if self.data[self.index] in "+-":
            self.index += 1
        while self.index < n and self.data[self.index].isdigit():
            self.index += 1

        token = self.data[start : self.index]
        if token in {"", "+", "-"}:
            self.index = start
            return None
        try:
            return int(token)
        except ValueError:
            self.index = start
            return None
