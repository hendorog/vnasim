"""Keysight E5080A/B model."""

from vnasim.models.common import CommonVNAModel
from vnasim.models.mixins import ENACommandsMixin, E5080CommandsMixin


class E5080Model(CommonVNAModel, ENACommandsMixin, E5080CommandsMixin):
    """Simulated Keysight E5080A/B VNA."""

    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None:
        self._segments: dict = {}
        super().__init__(
            num_ports=num_ports,
            idn=idn or "Keysight Technologies,E5080B,US00000001,A.15.00.00",
        )

    def _build_tree(self) -> None:
        self._register_core()
        self._register_ena()
        self._register_e5080()
