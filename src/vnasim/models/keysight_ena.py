"""Keysight/Agilent E5071B/C ENA model."""

from vnasim.models.common import CommonVNAModel
from vnasim.models.mixins import ENACommandsMixin


class E5071BModel(CommonVNAModel, ENACommandsMixin):
    """Simulated Keysight/Agilent E5071B/C ENA."""

    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None:
        super().__init__(
            num_ports=num_ports,
            idn=idn or "Agilent Technologies,E5071B,MY00000001,A.09.00",
        )

    def _build_tree(self) -> None:
        self._register_core()
        self._register_ena()
