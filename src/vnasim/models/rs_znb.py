"""Rohde & Schwarz ZNB/ZNA/ZVA model."""

from vnasim.models.common import CommonVNAModel
from vnasim.models.mixins import ENACommandsMixin, RSZNBCommandsMixin


class RSZNBModel(CommonVNAModel, ENACommandsMixin, RSZNBCommandsMixin):
    """Simulated Rohde & Schwarz ZNB/ZNA/ZVA."""

    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None:
        super().__init__(
            num_ports=num_ports,
            idn=idn or "Rohde&Schwarz,ZNB8-4Port,1234567890,3.40",
        )

    def _build_tree(self) -> None:
        self._register_core()
        self._register_ena()
        self._register_rs()
