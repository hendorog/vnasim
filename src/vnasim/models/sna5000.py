"""Siglent SNA5000A model."""

from vnasim.models.common import CommonVNAModel
from vnasim.models.mixins import SiglentCommandsMixin


class SNA5000Model(CommonVNAModel, SiglentCommandsMixin):
    """Simulated Siglent SNA5000A VNA."""

    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None:
        super().__init__(
            num_ports=num_ports,
            idn=idn or "Siglent Technologies,SNA5012A,SIM00001,2.3.1.3.1r1",
        )

    def _build_tree(self) -> None:
        self._register_core()
        self._register_siglent()
