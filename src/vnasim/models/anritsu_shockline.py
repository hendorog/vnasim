"""Anritsu ShockLine MS46xxx model."""

from vnasim.models.common import CommonVNAModel
from vnasim.models.mixins import ENACommandsMixin, AnritsuCommandsMixin


class AnritsuShockLineModel(CommonVNAModel, ENACommandsMixin, AnritsuCommandsMixin):
    """Simulated Anritsu ShockLine MS46xxx."""

    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None:
        super().__init__(
            num_ports=num_ports,
            idn=idn or "Anritsu,MS46522B,1234567890,1.0.0",
        )

    def _build_tree(self) -> None:
        self._register_core()
        self._register_ena()
        self._register_anritsu()
