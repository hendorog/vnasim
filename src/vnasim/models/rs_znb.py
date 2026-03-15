"""R&S ZNB/ZNA/ZVA model — extends E5071B with R&S-specific SCPI paths.

Key differences from E5071B:
- Named traces: ``CALC{ch}:PAR:SDEF 'name','S11'``
- Data queries use argument after ?: ``CALC{ch}:DATA? SDAT``
- Frequency list: ``CALC{ch}:DATA:STIM?``
- Trigger: ``INIT{ch}:CONT OFF`` + ``INIT{ch}:IMM`` (no TRIG:SING)
- Port count: ``INST:NPORT:COUN?``
- Cal coefficients: ``SENS{ch}:CORR:CDAT? 'TERM',port,port``
- Display window: ``DISP:WIND{ch}:STAT`` + ``DISP:WIND{ch}:TRAC:FEED``
"""

from __future__ import annotations

from vnasim.models.keysight_ena import E5071BModel
from vnasim.scpi.types import ParsedCommand


class RSZNBModel(E5071BModel):
    """Simulated Rohde & Schwarz ZNB/ZNA/ZVA."""

    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None:
        super().__init__(
            num_ports=num_ports,
            idn=idn or "Rohde&Schwarz,ZNB8-4Port,1234567890,3.40",
        )

    # -- R&S-specific handlers --

    def _handle_par_sdef(self, cmd: ParsedCommand) -> str | None:
        """``CALC{ch}:PAR:SDEF 'name','S11'`` — define named trace."""
        # Extract S-param from the quoted pair: 'name','S11'
        args = cmd.arguments.strip()
        parts = [p.strip().strip("'\"") for p in args.split(",")]
        param = parts[1] if len(parts) > 1 else parts[0]
        # Store on trace 1 (we only manage one trace)
        tr_state = self._tr(cmd)
        tr_state.parameter = param.upper()
        tr_state.channel = cmd.channel
        return None

    def _handle_par_sel_named(self, cmd: ParsedCommand) -> str | None:
        """``CALC{ch}:PAR:SEL 'name'`` — select trace by name (no-op)."""
        self._active_channel = cmd.channel
        return None

    def _handle_par_cat(self, cmd: ParsedCommand) -> str:
        """``CALC{ch}:PAR:CAT?`` — return trace catalog."""
        ch = cmd.channel
        for tr, ts in self._traces.items():
            if ts.channel == ch:
                return f"'VNALab','{ts.parameter}'"
        return "'VNALab','S11'"

    def _handle_par_del(self, cmd: ParsedCommand) -> str | None:
        """``CALC{ch}:PAR:DEL 'name'`` — accept but no-op."""
        return None

    def _handle_calc_data_with_arg(self, cmd: ParsedCommand) -> str | None:
        """``CALC{ch}:DATA? SDAT`` or ``CALC{ch}:DATA? FDAT``."""
        arg = cmd.arguments.strip().upper()
        if arg == "SDAT":
            return self._handle_calc_sel_sdata(cmd)
        elif arg == "FDAT":
            return self._handle_calc_sel_fdata(cmd)
        return None

    def _handle_calc_data_stim(self, cmd: ParsedCommand) -> str:
        """``CALC{ch}:DATA:STIM?`` — stimulus (frequency) data."""
        return self._handle_freq_data(cmd)

    def _handle_calc_data_call(self, cmd: ParsedCommand) -> str | None:
        """``CALC{ch}:DATA:CALL? SDAT`` — calibrated data."""
        return self._handle_calc_sel_sdata(cmd)

    def _handle_inst_nport_count(self, cmd: ParsedCommand) -> str:
        """``INST:NPORT:COUN?``"""
        return str(self._num_ports)

    def _handle_disp_wind_stat(self, cmd: ParsedCommand) -> str | None:
        """``DISP:WIND{ch}:STAT ON``"""
        if cmd.is_query:
            return "ON"
        return None

    def _handle_disp_trac_feed(self, cmd: ParsedCommand) -> str | None:
        """``DISP:WIND{ch}:TRAC{tr}:FEED 'name'``"""
        return None  # no-op

    def _handle_corr_cdata(self, cmd: ParsedCommand) -> str | None:
        """``SENS{ch}:CORR:CDAT`` — cal coefficient (R&S named terms)."""
        return self._handle_corr_coef_data(cmd)

    def _handle_corr_coll_meth(self, cmd: ParsedCommand) -> str | None:
        return None  # accept

    def _handle_corr_coll_save(self, cmd: ParsedCommand) -> str | None:
        return None  # accept

    # -- Tree --

    def _build_tree(self) -> None:
        super()._build_tree()
        t = self._tree

        # Named traces (parallel to indexed PAR{tr}:DEF)
        t.register(":CALCulate#:PARameter:SDEFine",
                   set_handler=self._handle_par_sdef)
        t.register(":CALCulate#:PARameter:SELect",
                   set_handler=self._handle_par_sel_named)
        t.register(":CALCulate#:PARameter:CATalog",
                   query_handler=self._handle_par_cat)
        t.register(":CALCulate#:PARameter:DELete",
                   set_handler=self._handle_par_del)

        # Data queries with argument after ?
        t.register(":CALCulate#:DATA",
                   query_handler=self._handle_calc_data_with_arg)
        t.register(":CALCulate#:DATA:STIMulus",
                   query_handler=self._handle_calc_data_stim)
        t.register(":CALCulate#:DATA:CALL",
                   query_handler=self._handle_calc_data_call)

        # Port count
        t.register(":INSTrument:NPORt:COUNt",
                   query_handler=self._handle_inst_nport_count)

        # Display window state and trace feed
        t.register(":DISPlay:WINDow#:STATe",
                   handler=self._handle_disp_wind_stat)
        t.register(":DISPlay:WINDow#:TRACe#:FEED",
                   set_handler=self._handle_disp_trac_feed)

        # Cal coefficients (R&S-style named terms)
        t.register(":SENSe#:CORRection:CDATa",
                   handler=self._handle_corr_cdata)

        # Cal method and save
        t.register(":SENSe#:CORRection:COLLect:METHod:DEFine",
                   set_handler=self._handle_corr_coll_meth)
        t.register(":SENSe#:CORRection:COLLect:SAVE:SELect:DEFault",
                   set_handler=self._handle_corr_coll_save)
