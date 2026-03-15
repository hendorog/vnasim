"""E5071B/C ENA model — extends SNA5000 with Keysight-specific SCPI paths.

The Keysight ENA uses the same core SCPI subsystems as the SNA5000 but
with several commands at different tree locations:

- ``:CALC{ch}:DATA:SDAT?`` instead of ``:CALC:SELected:DATA:SDATa?``
- ``:CALC{ch}:DATA:FDAT?`` instead of ``:CALC:SELected:DATA:FDATa?``
- ``:CALC{ch}:FORM`` instead of ``:CALC:SELected:FORMat``
- ``:CALC{ch}:PAR:COUN`` (parameter count — SNA5000 doesn't have this)
- ``:TRIG:SOUR`` / ``:TRIG:SING`` instead of ``:TRIG:SEQ:SOUR`` / ``:TRIG:SEQ:SING``
- ``:DISP:WIND{ch}:ACT`` for channel activation
- ``:FORM:DATA`` for data format negotiation
- ``:SERV:PORT:COUN?`` for port count query
- ``:SENS{ch}:BAND`` without ``:RESolution`` suffix for IF bandwidth

Most standard commands (frequency, sweep, averaging, correction, etc.)
already work via SCPI short-form matching on the SNA5000 tree.
"""

from __future__ import annotations

from vnasim.models.sna5000 import SNA5000Model
from vnasim.scpi.types import ParsedCommand


class E5071BModel(SNA5000Model):
    """Simulated Keysight/Agilent E5071B/C ENA."""

    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None:
        self._idn_override = idn or (
            "Agilent Technologies,E5071B,MY00000001,A.09.00"
        )
        super().__init__(num_ports=num_ports, idn=self._idn_override)

    # ------------------------------------------------------------------
    # ENA-specific handlers
    # ------------------------------------------------------------------

    def _handle_par_count(self, cmd: ParsedCommand) -> str | None:
        """`:CALC{ch}:PAR:COUN` — accept but ignore (single trace)."""
        if cmd.is_query:
            return "1"
        return None

    def _handle_form_data(self, cmd: ParsedCommand) -> str | None:
        """`:FORM:DATA` — accept but always use ASCII."""
        if cmd.is_query:
            return "ASC"
        return None

    def _handle_serv_port_count(self, cmd: ParsedCommand) -> str:
        return str(self._num_ports)

    def _handle_wind_activate(self, cmd: ParsedCommand) -> str | None:
        """`:DISP:WIND{ch}:ACT` — activate channel (ENA style)."""
        ch = cmd.channel
        self._active_channel = ch
        return None

    def _handle_ifbw_direct(self, cmd: ParsedCommand) -> str | None:
        """`:SENS{ch}:BAND` — IF bandwidth without :RESolution suffix."""
        return self._handle_ifbw(cmd)

    # ------------------------------------------------------------------
    # Tree construction — add ENA-specific paths on top of SNA5000
    # ------------------------------------------------------------------

    def _build_tree(self) -> None:
        # Start with the full SNA5000 command set
        super()._build_tree()
        t = self._tree

        # ENA data paths (parallel to SNA5000's :CALC:SELected:DATA:*)
        t.register(":CALCulate#:DATA:SDAT",
                   query_handler=self._handle_calc_sel_sdata)
        t.register(":CALCulate#:DATA:FDAT",
                   query_handler=self._handle_calc_sel_fdata)

        # ENA trace format (parallel to SNA5000's :CALC:SELected:FORMat)
        t.register(":CALCulate#:FORMat", handler=self._handle_calc_sel_fmt)

        # Parameter count
        t.register(":CALCulate#:PARameter:COUNt", handler=self._handle_par_count)

        # Trigger — ENA omits :SEQuence: level
        t.register(":TRIGger:SOURce", set_handler=self._handle_trig_src)
        t.register(":TRIGger:SING", set_handler=self._handle_trig_sing)

        # Channel activation — ENA uses :DISP:WIND{ch}:ACT
        t.register(":DISPlay:WINDow#:ACT",
                   set_handler=self._handle_wind_activate)

        # Data format negotiation
        t.register(":FORMat:DATA", handler=self._handle_form_data)

        # Service — port count
        t.register(":SERVice:PORT:COUNt",
                   query_handler=self._handle_serv_port_count)

        # IF bandwidth — ENA uses :SENS{ch}:BAND directly (no :RES suffix)
        t.register(":SENSe#:BANDwidth", handler=self._handle_ifbw_direct)

        # Averaging — ENA uses :SENS{ch}:AVER (no :STATe suffix)
        t.register(":SENSe#:AVERage", handler=self._handle_avg_state)

        # Smoothing — ENA uses :CALC{ch}:SMO (no :STATe suffix)
        t.register(":CALCulate#:SMOothing", handler=self._handle_smooth_state)

        # Display scale — ENA omits :SCALe: level
        # SNA5000: :DISP:WIND{ch}:TRAC1:Y:SCALe:RLEVel
        # ENA:    :DISP:WIND{ch}:TRAC1:Y:RLEV
        t.register(":DISPlay:WINDow#:TRACe#:Y:RLEVel",
                   handler=self._handle_disp_rlevel)
        t.register(":DISPlay:WINDow#:TRACe#:Y:PDIVision",
                   handler=self._handle_disp_pdiv)
        t.register(":DISPlay:WINDow#:TRACe#:Y:RPOSition",
                   handler=self._handle_disp_rpos)

        # Correction coefficient — ENA uses :SENS{ch}:CORR:COEF (shorter)
        # The SNA5000 already has :SENS{ch}:CORRection:COEFficient:DATA
        # which matches :SENS1:CORR:COEF via short-form. But the ENA
        # sends :SENS1:CORR:COEF? ED,1,1 (no :DATA level).
        # Register at the COEF level directly.
        t.register(":SENSe#:CORRection:COEFficient",
                   handler=self._handle_corr_coef_data)
