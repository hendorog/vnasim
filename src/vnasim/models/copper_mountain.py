"""Copper Mountain S2VNA/S4VNA/RVNA model."""

from vnasim.models.common import CommonVNAModel
from vnasim.models.mixins import ENACommandsMixin, CopperMountainCommandsMixin


class CopperMountainModel(CommonVNAModel, ENACommandsMixin, CopperMountainCommandsMixin):
    """Simulated Copper Mountain S2VNA / S4VNA / RVNA."""

    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None:
        super().__init__(
            num_ports=num_ports,
            idn=idn or "CMT,S2VNA,SN00001,1.0.0/1.0",
        )

    def _build_tree(self) -> None:
        self._register_core()
        self._register_ena()
        self._register_cmt()
