"""Anritsu ShockLine MS46xxx model — extends E5071B with Anritsu-specific paths.

Key differences from E5071B:
- Sweep type keyword: ``SWE:TYPe`` (not ``SWE:TYPE``)
- Trigger: ``SENS{ch}:HOLD:FUNC HOLD`` + ``TRIG:SING`` (blocking)
- Frequency list: ``SENS{ch}:FREQ:DATA?`` (like SNA5000)
- Segment sweep type: ``FSEGM`` (not ``SEGM``)
- Cal coefficients: named terms (``ED1``, ``EP1S``, etc.) without port arguments
"""

from __future__ import annotations

from vnasim.models.keysight_ena import E5071BModel
from vnasim.scpi.types import ParsedCommand


class AnritsuShockLineModel(E5071BModel):
    """Simulated Anritsu ShockLine MS46xxx."""

    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None:
        super().__init__(
            num_ports=num_ports,
            idn=idn or "Anritsu,MS46522B,1234567890,1.0.0",
        )

    # -- Anritsu-specific handlers --

    def _handle_swp_type_anritsu(self, cmd: ParsedCommand) -> str | None:
        """``SENS{ch}:SWE:TYP`` — sweep type (Anritsu abbreviation)."""
        state = self._ch(cmd)
        if cmd.is_query:
            return state.sweep_type
        state.sweep_type = cmd.arguments.strip()
        return None

    def _handle_hold_func(self, cmd: ParsedCommand) -> str | None:
        """``SENS{ch}:HOLD:FUNC`` — hold/continuous/single."""
        if cmd.is_query:
            return "HOLD"
        return None  # accept HOLD/CONT/SING

    def _handle_corr_coef_anritsu(self, cmd: ParsedCommand) -> str | None:
        """``SENS{ch}:CORR:COEF? term`` — Anritsu-style (no port args)."""
        state = self._ch(cmd)
        if cmd.is_query:
            # Arguments: "ED1" (just the term name)
            n = state.num_points
            term = cmd.arguments.strip().upper()
            key = term
            if key in state.cal_coefficients:
                return self._format_complex(state.cal_coefficients[key])
            # Ideal coefficients based on term type
            if "ET" in term or "ERFT" in term or "REFLTRACK" in term:
                return self._format_complex(self._ideal_coef("ER", n))
            return self._format_complex(self._ideal_coef("ED", n))
        # Set: "term,re1,im1,re2,im2,..."
        import numpy as np
        args = cmd.arguments.strip()
        parts = args.split(",")
        if parts:
            key = parts[0].strip().upper()
            vals = [float(x) for x in parts[1:]]
            data = np.array(vals[0::2]) + 1j * np.array(vals[1::2])
            state.cal_coefficients[key] = data
        return None

    def _handle_corr_coll_type(self, cmd: ParsedCommand) -> str:
        """``SENS{ch}:CORR:COLL:TYP?``"""
        return "NONE"

    def _handle_corr_coef_port(self, cmd: ParsedCommand) -> str | None:
        """Accept any calibration port/method command."""
        return None

    # -- Tree --

    def _build_tree(self) -> None:
        super()._build_tree()
        t = self._tree

        # Sweep type — Anritsu uses :SWE:TYPe (short form TYP, 3 chars)
        # Can't reuse the existing TYPE registration (short form = TYPE, 4 chars)
        t.register(":SENSe#:SWEep:TYPe",
                   handler=self._handle_swp_type_anritsu)

        # Hold / trigger control
        t.register(":SENSe#:HOLD:FUNCtion",
                   handler=self._handle_hold_func)

        # Frequency list — Anritsu uses :SENS:FREQ:DATA? (like SNA5000)
        # Already registered in SNA5000 base

        # Cal coefficients — Anritsu single-argument style
        # Override the E5071B CORR:COEF handler
        t.register(":SENSe#:CORRection:COEFficient",
                   handler=self._handle_corr_coef_anritsu)

        # Cal collection type query
        t.register(":SENSe#:CORRection:COLLect:TYPe",
                   query_handler=self._handle_corr_coll_type)

        # Per-port cal method commands (accept all)
        t.register(":SENSe#:CORRection:COEFficient:PORT12:FULL2",
                   set_handler=self._handle_corr_coef_port)
        t.register(":SENSe#:CORRection:COEFficient:PORT#:FULL1",
                   set_handler=self._handle_corr_coef_port)
        t.register(":SENSe#:CORRection:COEFficient:PORT#:RESP1",
                   set_handler=self._handle_corr_coef_port)
        t.register(":SENSe#:CORRection:COEFficient:PORT12:1P2PF",
                   set_handler=self._handle_corr_coef_port)
        t.register(":SENSe#:CORRection:COEFficient:PORT12:TFRF",
                   set_handler=self._handle_corr_coef_port)
