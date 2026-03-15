"""Copper Mountain S2VNA/S4VNA model — extends E5071B with CMT-specific paths.

Key differences from E5071B:
- IFBW via ``:SENS{ch}:BWID`` (not ``:BAND``)
- Smoothing via ``:CALC{ch}:TRAC:SMOothing`` (not ``:CALC:SMO``)
- Frequency list via ``:CALC{ch}:DATA:XAX?``
- No sweep time query (estimated from points/IFBW)
"""

from __future__ import annotations

from vnasim.models.keysight_ena import E5071BModel
from vnasim.scpi.types import ParsedCommand


class CopperMountainModel(E5071BModel):
    """Simulated Copper Mountain S2VNA / S4VNA / RVNA."""

    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None:
        super().__init__(
            num_ports=num_ports,
            idn=idn or "CMT,S2VNA,SN00001,1.0.0/1.0",
        )

    def _handle_xax(self, cmd: ParsedCommand) -> str:
        """``CALC{ch}:DATA:XAX?`` — X-axis frequency data."""
        return self._handle_freq_data(cmd)

    def _handle_trac_smooth_state(self, cmd: ParsedCommand) -> str | None:
        """``CALC{ch}:TRAC:SMO``"""
        return self._handle_smooth_state(cmd)

    def _handle_trac_smooth_aper(self, cmd: ParsedCommand) -> str | None:
        """``CALC{ch}:TRAC:SMO:APER``"""
        return self._handle_smooth_aperture(cmd)

    def _build_tree(self) -> None:
        super()._build_tree()
        t = self._tree

        # IFBW — CMT uses :BWID instead of :BAND
        t.register(":SENSe#:BWIDth", handler=self._handle_ifbw_direct)

        # Frequency list — CMT uses :CALC:DATA:XAX?
        t.register(":CALCulate#:DATA:XAXis",
                   query_handler=self._handle_xax)

        # Smoothing — CMT uses :CALC:TRAC:SMOO (not :CALC:SMO)
        t.register(":CALCulate#:TRACe:SMOothing",
                   handler=self._handle_trac_smooth_state)
        t.register(":CALCulate#:TRACe:SMOothing:APERture",
                   handler=self._handle_trac_smooth_aper)
