"""SCPI command data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


class Unhandled:
    """Returned by dispatch/handle when a command is not recognised.

    Carries the raw command string and a short reason so the server
    can log it with surrounding context.
    """

    __slots__ = ("raw", "reason")

    def __init__(self, raw: str, reason: str) -> None:
        self.raw = raw
        self.reason = reason

    def __repr__(self) -> str:
        return f"Unhandled({self.raw!r}, {self.reason!r})"


@dataclass
class ParsedCommand:
    """A parsed SCPI command ready for dispatch."""

    raw: str
    is_query: bool
    arguments: str
    suffixes: list[int] = field(default_factory=list)

    @property
    def channel(self) -> int:
        """First numeric suffix (channel), defaults to 1."""
        return self.suffixes[0] if self.suffixes else 1

    @property
    def trace(self) -> int:
        """Second numeric suffix (trace), defaults to 1."""
        return self.suffixes[1] if len(self.suffixes) > 1 else 1
