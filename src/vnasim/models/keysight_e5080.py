"""E5080A/B model — extends E5071B with E5080-specific SCPI paths.

The E5080 differs from the E5071B in several key areas:

- **Measurement model**: ``CALC{ch}:MEAS{m}:DEF`` instead of ``CALC:PAR{tr}:DEF``
- **Data queries**: ``CALC{ch}:MEAS{m}:DATA:SDATA?`` / ``FDATA?``
- **X-axis**: ``CALC{ch}:MEAS{m}:X?`` instead of ``SENS:FREQ:DATA?``
- **Trigger**: ``SENS{ch}:SWE:MODE SING`` + ``INIT{ch}:IMM`` (no TRIG:SING)
- **Port detection**: ``SYST:CAP:HARD:PORT:INT:COUN?``
- **Display**: measurement-indexed ``DISP:MEAS{m}:Y:RLEV``
- **Cal Sets**: ``SENS{ch}:CORR:CSET:DATA`` instead of ``CORR:COEF``
- **Segments**: per-segment commands instead of bulk ``SEGM:DATA``
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vnasim.models.keysight_ena import E5071BModel
from vnasim.scpi.types import ParsedCommand


@dataclass
class SegmentState:
    start_freq: float = 1e6
    stop_freq: float = 6e9
    num_points: int = 201
    if_bandwidth: float = 1000.0


class E5080Model(E5071BModel):
    """Simulated Keysight E5080A/B VNA."""

    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None:
        self._segments: dict[int, list[SegmentState]] = {}
        super().__init__(
            num_ports=num_ports,
            idn=idn or "Keysight Technologies,E5080B,US00000001,A.15.00.00",
        )

    # ------------------------------------------------------------------
    # E5080-specific handlers
    # ------------------------------------------------------------------

    def _handle_meas_def(self, cmd: ParsedCommand) -> str | None:
        """``CALC{ch}:MEAS{m}:DEF "S11"`` — define measurement."""
        tr_state = self._tr(cmd)
        if cmd.is_query:
            return tr_state.parameter
        tr_state.parameter = cmd.arguments.strip().strip('"')
        tr_state.channel = cmd.channel
        return None

    def _handle_meas_par(self, cmd: ParsedCommand) -> str | None:
        """``CALC{ch}:MEAS{m}:PAR`` — query/set parameter name."""
        tr_state = self._tr(cmd)
        if cmd.is_query:
            return tr_state.parameter
        tr_state.parameter = cmd.arguments.strip().strip('"')
        return None

    def _handle_meas_sdata(self, cmd: ParsedCommand) -> str:
        """``CALC{ch}:MEAS{m}:DATA:SDATA?``"""
        return self._handle_calc_sel_sdata(cmd)

    def _handle_meas_fdata(self, cmd: ParsedCommand) -> str:
        """``CALC{ch}:MEAS{m}:DATA:FDATA?``"""
        return self._handle_calc_sel_fdata(cmd)

    def _handle_meas_x(self, cmd: ParsedCommand) -> str:
        """``CALC{ch}:MEAS{m}:X?`` — X-axis (frequency) data."""
        return self._handle_freq_data(cmd)

    def _handle_meas_form(self, cmd: ParsedCommand) -> str | None:
        """``CALC{ch}:MEAS{m}:FORM`` — trace format per measurement."""
        # Apply to the trace corresponding to the measurement number
        tr = cmd.trace
        if tr not in self._traces:
            from vnasim.models.sna5000 import TraceState
            self._traces[tr] = TraceState(channel=cmd.channel)
        if cmd.is_query:
            return self._traces[tr].format
        self._traces[tr].format = cmd.arguments.strip()
        return None

    def _handle_meas_smooth_state(self, cmd: ParsedCommand) -> str | None:
        """``CALC{ch}:MEAS{m}:SMO``"""
        return self._handle_smooth_state(cmd)

    def _handle_meas_smooth_aper(self, cmd: ParsedCommand) -> str | None:
        """``CALC{ch}:MEAS{m}:SMO:APER``"""
        return self._handle_smooth_aperture(cmd)

    def _handle_swp_mode(self, cmd: ParsedCommand) -> str | None:
        """``SENS{ch}:SWE:MODE`` — accept SING/CONT."""
        if cmd.is_query:
            return "SING"
        return None

    def _handle_init_imm(self, cmd: ParsedCommand) -> str | None:
        """``INIT{ch}:IMM`` — immediate initiation (no-op)."""
        return None

    def _handle_syst_port_count(self, cmd: ParsedCommand) -> str:
        """``SYST:CAP:HARD:PORT:INT:COUN?``"""
        return str(self._num_ports)

    def _handle_chan_catalog(self, cmd: ParsedCommand) -> str:
        """``SYST:CHAN:CAT?`` — returns quoted comma-separated channel list."""
        chs = ",".join(str(ch) for ch in sorted(self._channels))
        return f'"{chs}"'

    def _handle_disp_wind_state(self, cmd: ParsedCommand) -> str | None:
        """``DISP:WIND1:STATE ON``"""
        return None  # no-op

    def _handle_disp_meas_feed(self, cmd: ParsedCommand) -> str | None:
        """``DISP:MEAS{m}:FEED 1``"""
        return None  # no-op

    def _handle_disp_meas_rlev(self, cmd: ParsedCommand) -> str | None:
        ch_num = self._active_channel
        if ch_num not in self._channels:
            from vnasim.models.sna5000 import ChannelState
            self._channels[ch_num] = ChannelState()
        state = self._channels[ch_num]
        if cmd.is_query:
            return str(state.ref_level)
        state.ref_level = float(cmd.arguments)
        return None

    def _handle_disp_meas_pdiv(self, cmd: ParsedCommand) -> str | None:
        ch_num = self._active_channel
        if ch_num not in self._channels:
            from vnasim.models.sna5000 import ChannelState
            self._channels[ch_num] = ChannelState()
        state = self._channels[ch_num]
        if cmd.is_query:
            return str(state.per_div)
        state.per_div = float(cmd.arguments)
        return None

    def _handle_disp_meas_rpos(self, cmd: ParsedCommand) -> str | None:
        ch_num = self._active_channel
        if ch_num not in self._channels:
            from vnasim.models.sna5000 import ChannelState
            self._channels[ch_num] = ChannelState()
        state = self._channels[ch_num]
        if cmd.is_query:
            return str(state.ref_position)
        state.ref_position = int(float(cmd.arguments))
        return None

    # -- Cal Set stubs --

    def _handle_cset_create(self, cmd: ParsedCommand) -> str | None:
        return None

    def _handle_cset_data(self, cmd: ParsedCommand) -> str | None:
        """``SENS{ch}:CORR:CSET:DATA`` — cal set coefficient access."""
        return self._handle_corr_coef_data(cmd)

    def _handle_cset_save(self, cmd: ParsedCommand) -> str | None:
        return None

    def _handle_cset_activate(self, cmd: ParsedCommand) -> str | None:
        return None

    def _handle_cset_act_name(self, cmd: ParsedCommand) -> str:
        return '"vna_frontend_ch1"'

    # -- Per-segment commands --

    def _handle_seg_del_all(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        self._segments[ch] = []
        return None

    def _handle_seg_count(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        return str(len(self._segments.get(ch, [])))

    def _handle_seg_add(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if ch not in self._segments:
            self._segments[ch] = []
        self._segments[ch].append(SegmentState())
        return None

    def _get_segment(self, cmd: ParsedCommand) -> SegmentState:
        ch = cmd.channel
        # Second suffix is segment number (1-based)
        s = cmd.trace - 1  # trace property returns suffixes[1]
        segs = self._segments.get(ch, [])
        while len(segs) <= s:
            segs.append(SegmentState())
        return segs[s]

    def _handle_seg_freq_start(self, cmd: ParsedCommand) -> str | None:
        seg = self._get_segment(cmd)
        if cmd.is_query:
            return str(seg.start_freq)
        seg.start_freq = float(cmd.arguments)
        return None

    def _handle_seg_freq_stop(self, cmd: ParsedCommand) -> str | None:
        seg = self._get_segment(cmd)
        if cmd.is_query:
            return str(seg.stop_freq)
        seg.stop_freq = float(cmd.arguments)
        return None

    def _handle_seg_swp_points(self, cmd: ParsedCommand) -> str | None:
        seg = self._get_segment(cmd)
        if cmd.is_query:
            return str(seg.num_points)
        seg.num_points = int(float(cmd.arguments))
        return None

    def _handle_seg_bwid(self, cmd: ParsedCommand) -> str | None:
        seg = self._get_segment(cmd)
        if cmd.is_query:
            return str(seg.if_bandwidth)
        seg.if_bandwidth = float(cmd.arguments)
        return None

    def _handle_seg_bwid_cont(self, cmd: ParsedCommand) -> str | None:
        return None  # accept but no-op

    def _handle_seg_pow_cont(self, cmd: ParsedCommand) -> str | None:
        return None  # accept but no-op

    # ------------------------------------------------------------------
    # Tree construction
    # ------------------------------------------------------------------

    def _build_tree(self) -> None:
        super()._build_tree()
        t = self._tree

        # -- Measurement model (CALC:MEAS instead of CALC:PAR) --
        t.register(":CALCulate#:MEASure#:DEFine",
                   handler=self._handle_meas_def)
        t.register(":CALCulate#:MEASure#:PARameter",
                   handler=self._handle_meas_par)
        t.register(":CALCulate#:MEASure#:DATA:SDATA",
                   query_handler=self._handle_meas_sdata)
        t.register(":CALCulate#:MEASure#:DATA:FDATA",
                   query_handler=self._handle_meas_fdata)
        t.register(":CALCulate#:MEASure#:X",
                   query_handler=self._handle_meas_x)
        t.register(":CALCulate#:MEASure#:FORMat",
                   handler=self._handle_meas_form)
        t.register(":CALCulate#:MEASure#:SMOothing",
                   handler=self._handle_meas_smooth_state)
        t.register(":CALCulate#:MEASure#:SMOothing:APERture",
                   handler=self._handle_meas_smooth_aper)

        # -- Sweep mode & initiate --
        t.register(":SENSe#:SWEep:MODE", handler=self._handle_swp_mode)
        t.register(":INITiate#:IMMediate", set_handler=self._handle_init_imm)

        # -- System queries --
        t.register(":SYSTem:CAPability:HARDware:PORT:INTernal:COUNt",
                   query_handler=self._handle_syst_port_count)
        t.register(":SYSTem:CHANnel:CATalog",
                   query_handler=self._handle_chan_catalog)

        # -- Display (measurement-indexed) --
        t.register(":DISPlay:WINDow#:STATe",
                   set_handler=self._handle_disp_wind_state)
        t.register(":DISPlay:MEASure#:FEED",
                   set_handler=self._handle_disp_meas_feed)
        t.register(":DISPlay:MEASure#:Y:RLEVel",
                   handler=self._handle_disp_meas_rlev)
        t.register(":DISPlay:MEASure#:Y:PDIVision",
                   handler=self._handle_disp_meas_pdiv)
        t.register(":DISPlay:MEASure#:Y:RPOSition",
                   handler=self._handle_disp_meas_rpos)

        # -- Cal Set commands --
        t.register(":SENSe#:CORRection:CSET:CREate",
                   set_handler=self._handle_cset_create)
        t.register(":SENSe#:CORRection:CSET:CREate:DEFault",
                   set_handler=self._handle_cset_create)
        t.register(":SENSe#:CORRection:CSET:DATA",
                   handler=self._handle_cset_data)
        t.register(":SENSe#:CORRection:CSET:SAVE",
                   set_handler=self._handle_cset_save)
        t.register(":SENSe#:CORRection:CSET:ACTivate",
                   handler=self._handle_cset_activate)

        # -- Per-segment commands --
        t.register(":SENSe#:SEGMent:DELete:ALL",
                   set_handler=self._handle_seg_del_all)
        t.register(":SENSe#:SEGMent:COUNt",
                   query_handler=self._handle_seg_count)
        t.register(":SENSe#:SEGMent#:ADD",
                   set_handler=self._handle_seg_add)
        t.register(":SENSe#:SEGMent#:FREQuency:STARt",
                   handler=self._handle_seg_freq_start)
        t.register(":SENSe#:SEGMent#:FREQuency:STOP",
                   handler=self._handle_seg_freq_stop)
        t.register(":SENSe#:SEGMent#:SWEep:POINts",
                   handler=self._handle_seg_swp_points)
        t.register(":SENSe#:SEGMent#:BWIDth",
                   handler=self._handle_seg_bwid)
        t.register(":SENSe#:SEGMent:BWIDth:CONTrol",
                   set_handler=self._handle_seg_bwid_cont)
        t.register(":SENSe#:SEGMent:POWer:CONTrol",
                   set_handler=self._handle_seg_pow_cont)

        # -- CW frequency (E5080 has it, like SNA5000) --
        t.register(":SENSe#:FREQuency:CW", handler=self._handle_freq_cw)
