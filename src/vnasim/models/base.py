"""Abstract VNA model interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from vnasim.scpi.parser import SCPITree
from vnasim.scpi.types import Unhandled


class VNAModel(ABC):
    """Base class for simulated VNA instruments.

    Subclasses build a SCPI command tree and maintain instrument state.
    """

    @abstractmethod
    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None: ...

    @property
    @abstractmethod
    def tree(self) -> SCPITree:
        """Return the SCPI command tree for this model."""
        ...

    def handle(self, command: str) -> str | None | Unhandled:
        """Process a SCPI command string.

        Returns ``str`` for query responses, ``None`` for handled write
        commands, or :class:`Unhandled` when the command is not recognised.
        """
        return self.tree.dispatch(command)
