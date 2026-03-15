"""SNA5000 VNA model — SCPI state machine for the Siglent SNA5000A series."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

from vnasim.data.synthetic import generate_param, isolation_response
from vnasim.models.base import VNAModel
from vnasim.scpi.parser import SCPITree
from vnasim.scpi.types import ParsedCommand

logger = logging.getLogger(__name__)


@dataclass
class ChannelState:
    start_freq: float = 100e6
    stop_freq: float = 3e9
    num_points: int = 1001
    if_bw: float = 1000.0
    sweep_type: str = "LINear"
    cw_freq: float = 1e9
    power: float = 0.0
    avg_state: bool = False
    avg_count: int = 1
    smooth_state: bool = False
    smooth_aperture: float = 5.0
    corr_state: bool = False
    ref_level: float = 0.0
    per_div: float = 10.0
    ref_position: int = 5
    segment_data: str = ""
    sweep_time_auto: bool = True
    sweep_time: float = 0.05
    topology: str = ""
    init_continuous: bool = True
    cal_coefficients: dict = field(default_factory=dict)


@dataclass
class TraceState:
    channel: int = 1
    parameter: str = "S11"
    format: str = "MLOGarithmic"


class SNA5000Model(VNAModel):
    """Simulated Siglent SNA5000A VNA."""

    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None:
        self._num_ports = num_ports
        self._idn = idn or "Siglent Technologies,SNA5012A,SIM00001,2.3.1.3.1r1"
        self._channels: dict[int, ChannelState] = {1: ChannelState()}
        self._traces: dict[int, TraceState] = {1: TraceState(channel=1)}
        self._active_channel = 1
        self._active_trace = 1
        self._next_channel = 2
        self._next_trace = 2
        self._trigger_scope = "ALL"
        self._trigger_source = "INTernal"
        self._tree = SCPITree()
        self._build_tree()

    @property
    def tree(self) -> SCPITree:
        return self._tree

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ch(self, cmd: ParsedCommand) -> ChannelState:
        """Get channel state, creating on first access."""
        ch = cmd.channel
        if ch not in self._channels:
            self._channels[ch] = ChannelState()
        return self._channels[ch]

    def _tr(self, cmd: ParsedCommand) -> TraceState:
        """Get trace state, creating on first access."""
        tr = cmd.trace
        if tr not in self._traces:
            self._traces[tr] = TraceState(channel=cmd.channel)
        return self._traces[tr]

    def _freq_grid(self, state: ChannelState) -> np.ndarray:
        return np.linspace(state.start_freq, state.stop_freq, state.num_points)

    def _format_complex(self, data: np.ndarray) -> str:
        """Format complex array as comma-separated re,im pairs."""
        parts: list[str] = []
        for c in data:
            parts.append(str(c.real))
            parts.append(str(c.imag))
        return ",".join(parts)

    def _generate_sdata(self, param: str, state: ChannelState) -> str:
        """Generate complex S-parameter data for the given parameter."""
        freqs = self._freq_grid(state)
        # Standard S-parameters
        p = param.strip().strip('"').upper()
        if len(p) >= 3 and p[0] == 'S' and p[1:].isdigit():
            data = generate_param(p, freqs, self._num_ports)
        else:
            # Expression-based: return flat response
            data = isolation_response(freqs, isolation_dB=-20.0)
        return self._format_complex(data)

    def _apply_format(
        self, data: np.ndarray, fmt: str,
    ) -> str:
        """Apply display format to complex data, return comma-separated pairs."""
        f = fmt.upper()
        parts: list[str] = []
        for c in data:
            if f.startswith("MLOG"):
                val = 20.0 * np.log10(max(abs(c), 1e-15))
                parts.extend([str(val), "0"])
            elif f.startswith("PHAS"):
                parts.extend([str(np.degrees(np.angle(c))), "0"])
            elif f.startswith("MLIN"):
                parts.extend([str(abs(c)), "0"])
            elif f == "SWR":
                r = min(abs(c), 0.9999)
                parts.extend([str((1 + r) / (1 - r)), "0"])
            elif f == "REAL":
                parts.extend([str(c.real), "0"])
            elif f.startswith("IMAG"):
                parts.extend(["0", str(c.imag)])
            elif f.startswith("GDEL"):
                parts.extend(["0", "0"])
            elif f.startswith("SMIT") or f.startswith("POL"):
                parts.extend([str(c.real), str(c.imag)])
            else:
                parts.extend([str(c.real), str(c.imag)])
        return ",".join(parts)

    def _ideal_coef(self, term: str, n: int) -> np.ndarray:
        """Return ideal calibration coefficients for the given error term."""
        if term.upper() in ("ER", "ET"):
            return np.ones(n, dtype=complex)
        return np.zeros(n, dtype=complex)

    # ------------------------------------------------------------------
    # IEEE 488.2 common commands
    # ------------------------------------------------------------------

    def _handle_idn(self, cmd: ParsedCommand) -> str:
        return self._idn

    def _handle_rst(self, cmd: ParsedCommand) -> str | None:
        self._channels = {1: ChannelState()}
        self._traces = {1: TraceState(channel=1)}
        self._active_channel = 1
        self._active_trace = 1
        self._next_channel = 2
        self._next_trace = 2
        return None

    def _handle_opc(self, cmd: ParsedCommand) -> str:
        return "1"

    # ------------------------------------------------------------------
    # Frequency
    # ------------------------------------------------------------------

    def _handle_freq_start(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.start_freq)
        state.start_freq = float(cmd.arguments)
        return None

    def _handle_freq_stop(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.stop_freq)
        state.stop_freq = float(cmd.arguments)
        return None

    def _handle_freq_data(self, cmd: ParsedCommand) -> str:
        state = self._ch(cmd)
        freqs = self._freq_grid(state)
        return ",".join(str(f) for f in freqs)

    def _handle_freq_cw(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.cw_freq)
        state.cw_freq = float(cmd.arguments)
        return None

    # ------------------------------------------------------------------
    # Sweep
    # ------------------------------------------------------------------

    def _handle_swp_points(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.num_points)
        state.num_points = int(float(cmd.arguments))
        return None

    def _handle_swp_type(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return state.sweep_type
        state.sweep_type = cmd.arguments.strip()
        return None

    def _handle_swp_time(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.sweep_time)
        state.sweep_time = float(cmd.arguments)
        return None

    def _handle_swp_time_auto(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        state.sweep_time_auto = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    # ------------------------------------------------------------------
    # IF bandwidth
    # ------------------------------------------------------------------

    def _handle_ifbw(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.if_bw)
        state.if_bw = float(cmd.arguments)
        return None

    # ------------------------------------------------------------------
    # Calculate — parameter / format
    # ------------------------------------------------------------------

    def _handle_calc_par_def(self, cmd: ParsedCommand) -> str | None:
        tr_state = self._tr(cmd)
        if cmd.is_query:
            return tr_state.parameter
        tr_state.parameter = cmd.arguments.strip().strip('"')
        tr_state.channel = cmd.channel
        return None

    def _handle_calc_par_sel(self, cmd: ParsedCommand) -> str | None:
        tr = cmd.trace
        self._active_trace = tr
        self._active_channel = cmd.channel
        return None

    def _handle_calc_sel_fmt(self, cmd: ParsedCommand) -> str | None:
        # Apply to the active trace
        if self._active_trace in self._traces:
            self._traces[self._active_trace].format = cmd.arguments.strip()
        return None

    def _handle_calc_sel_fdata(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        state = self._ch(cmd)
        # Find the selected trace for this channel
        tr_state = None
        for t in self._traces.values():
            if t.channel == ch:
                tr_state = t
                break
        if tr_state is None:
            tr_state = TraceState(channel=ch)
        freqs = self._freq_grid(state)
        param = tr_state.parameter.strip().strip('"').upper()
        if len(param) >= 3 and param[0] == 'S' and param[1:].isdigit():
            data = generate_param(param, freqs, self._num_ports)
        else:
            data = isolation_response(freqs, isolation_dB=-20.0)
        return self._apply_format(data, tr_state.format)

    def _handle_calc_sel_sdata(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        state = self._ch(cmd)
        tr_state = None
        for t in self._traces.values():
            if t.channel == ch:
                tr_state = t
                break
        if tr_state is None:
            tr_state = TraceState(channel=ch)
        return self._generate_sdata(tr_state.parameter, state)

    # ------------------------------------------------------------------
    # Data access — raw / corrected
    # ------------------------------------------------------------------

    def _handle_data_raw(self, cmd: ParsedCommand) -> str:
        state = self._ch(cmd)
        return self._generate_sdata(cmd.arguments, state)

    def _handle_data_corr(self, cmd: ParsedCommand) -> str:
        state = self._ch(cmd)
        return self._generate_sdata(cmd.arguments, state)

    # ------------------------------------------------------------------
    # Averaging
    # ------------------------------------------------------------------

    def _handle_avg_state(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return "ON" if state.avg_state else "OFF"
        state.avg_state = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_avg_count(self, cmd: ParsedCommand) -> str:
        return str(self._ch(cmd).avg_count)

    # ------------------------------------------------------------------
    # Smoothing
    # ------------------------------------------------------------------

    def _handle_smooth_state(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return "ON" if state.smooth_state else "OFF"
        state.smooth_state = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_smooth_aperture(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.smooth_aperture)
        state.smooth_aperture = float(cmd.arguments)
        return None

    # ------------------------------------------------------------------
    # Source power
    # ------------------------------------------------------------------

    def _handle_src_power(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.power)
        state.power = float(cmd.arguments)
        return None

    # ------------------------------------------------------------------
    # Display — scale
    # ------------------------------------------------------------------

    def _handle_disp_rlevel(self, cmd: ParsedCommand) -> str | None:
        ch_num = cmd.suffixes[0] if cmd.suffixes else 1
        if ch_num not in self._channels:
            self._channels[ch_num] = ChannelState()
        state = self._channels[ch_num]
        if cmd.is_query:
            return str(state.ref_level)
        state.ref_level = float(cmd.arguments)
        return None

    def _handle_disp_pdiv(self, cmd: ParsedCommand) -> str | None:
        ch_num = cmd.suffixes[0] if cmd.suffixes else 1
        if ch_num not in self._channels:
            self._channels[ch_num] = ChannelState()
        state = self._channels[ch_num]
        if cmd.is_query:
            return str(state.per_div)
        state.per_div = float(cmd.arguments)
        return None

    def _handle_disp_rpos(self, cmd: ParsedCommand) -> str | None:
        ch_num = cmd.suffixes[0] if cmd.suffixes else 1
        if ch_num not in self._channels:
            self._channels[ch_num] = ChannelState()
        state = self._channels[ch_num]
        if cmd.is_query:
            return str(state.ref_position)
        state.ref_position = int(float(cmd.arguments))
        return None

    # ------------------------------------------------------------------
    # Display — channel / trace management
    # ------------------------------------------------------------------

    def _handle_chan_list(self, cmd: ParsedCommand) -> str:
        return ",".join(str(ch) for ch in sorted(self._channels))

    def _handle_trace_list(self, cmd: ParsedCommand) -> str:
        return ",".join(str(tr) for tr in sorted(self._traces))

    def _handle_chan_trace_list(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        traces = [
            tr for tr, ts in sorted(self._traces.items())
            if ts.channel == ch
        ]
        return ",".join(str(t) for t in traces) if traces else "1"

    def _handle_add_function(self, cmd: ParsedCommand) -> str | None:
        ch = self._next_channel
        tr = self._next_trace
        self._channels[ch] = ChannelState()
        self._traces[tr] = TraceState(channel=ch)
        self._next_channel += 1
        self._next_trace += 1
        return None

    def _handle_chan_activate(self, cmd: ParsedCommand) -> str | None:
        self._active_channel = cmd.channel
        return None

    def _handle_trace_activate(self, cmd: ParsedCommand) -> str | None:
        tr = cmd.channel  # First suffix is the trace number here
        self._active_trace = tr
        if tr in self._traces:
            self._active_channel = self._traces[tr].channel
        return None

    # ------------------------------------------------------------------
    # Trigger / Initiate
    # ------------------------------------------------------------------

    def _handle_init_cont(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        state.init_continuous = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_trig_scope(self, cmd: ParsedCommand) -> str | None:
        self._trigger_scope = cmd.arguments.strip()
        return None

    def _handle_trig_src(self, cmd: ParsedCommand) -> str | None:
        self._trigger_source = cmd.arguments.strip()
        return None

    def _handle_trig_sing(self, cmd: ParsedCommand) -> str | None:
        # No-op — simulator doesn't need to delay
        return None

    # ------------------------------------------------------------------
    # Balanced topology
    # ------------------------------------------------------------------

    def _handle_dtopology(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return state.topology or "NONE"
        state.topology = cmd.arguments.strip()
        return None

    # ------------------------------------------------------------------
    # Correction
    # ------------------------------------------------------------------

    def _handle_corr_state(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return "ON" if state.corr_state else "OFF"
        state.corr_state = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_corr_coef_data(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            # Arguments: "ED,1,1"
            args = cmd.arguments.strip()
            n = state.num_points
            key = args.upper()
            if key in state.cal_coefficients:
                return self._format_complex(state.cal_coefficients[key])
            # Return ideal coefficients
            term = args.split(",")[0].strip() if args else "ED"
            return self._format_complex(self._ideal_coef(term, n))
        # Set: arguments = "ED,1,1,re1,im1,re2,im2,..."
        args = cmd.arguments.strip()
        parts = args.split(",")
        if len(parts) >= 3:
            key = ",".join(parts[:3]).upper()
            vals = [float(x) for x in parts[3:]]
            data = np.array(vals[0::2]) + 1j * np.array(vals[1::2])
            state.cal_coefficients[key] = data
        return None

    def _handle_corr_coef_save(self, cmd: ParsedCommand) -> str | None:
        return None  # No-op — coefficients already stored

    def _handle_corr_meth(self, cmd: ParsedCommand) -> str | None:
        return None  # Accept but no-op

    # ------------------------------------------------------------------
    # Segment data
    # ------------------------------------------------------------------

    def _handle_seg_data(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return state.segment_data or "5,0,0,0,0,0,0"
        state.segment_data = cmd.arguments.strip()
        return None

    # ------------------------------------------------------------------
    # Tree construction
    # ------------------------------------------------------------------

    def _build_tree(self) -> None:
        t = self._tree

        # IEEE 488.2
        t.register("*IDN", query_handler=self._handle_idn)
        t.register("*RST", set_handler=self._handle_rst)
        t.register("*OPC", query_handler=self._handle_opc)

        # Frequency
        t.register(":SENSe#:FREQuency:STARt", handler=self._handle_freq_start)
        t.register(":SENSe#:FREQuency:STOP", handler=self._handle_freq_stop)
        t.register(":SENSe#:FREQuency:DATA", query_handler=self._handle_freq_data)
        t.register(":SENSe#:FREQuency:CW", handler=self._handle_freq_cw)

        # Sweep
        t.register(":SENSe#:SWEep:POINts", handler=self._handle_swp_points)
        t.register(":SENSe#:SWEep:TYPE", handler=self._handle_swp_type)
        t.register(":SENSe#:SWEep:TIME", handler=self._handle_swp_time)
        t.register(":SENSe#:SWEep:TIME:AUTO", set_handler=self._handle_swp_time_auto)

        # IF bandwidth
        t.register(":SENSe#:BANDwidth:RESolution", handler=self._handle_ifbw)

        # Calculate — parameter definition
        t.register(":CALCulate#:PARameter#:DEFine", handler=self._handle_calc_par_def)
        t.register(":CALCulate#:PARameter#:SELect", set_handler=self._handle_calc_par_sel)

        # Calculate — selected trace data
        t.register(":CALCulate#:SELected:FORMat", set_handler=self._handle_calc_sel_fmt)
        t.register(":CALCulate#:SELected:DATA:FDATa",
                   query_handler=self._handle_calc_sel_fdata)
        t.register(":CALCulate#:SELected:DATA:SDATa",
                   query_handler=self._handle_calc_sel_sdata)

        # Smoothing (under :CALCulate)
        t.register(":CALCulate#:SMOothing:STATe", handler=self._handle_smooth_state)
        t.register(":CALCulate#:SMOothing:APERture", handler=self._handle_smooth_aperture)

        # Balanced topology
        t.register(":CALCulate#:DTOPology", handler=self._handle_dtopology)

        # Data access
        t.register(":SENSe#:DATA:RAWData", query_handler=self._handle_data_raw)
        t.register(":SENSe#:DATA:CORRdata", query_handler=self._handle_data_corr)

        # Averaging
        t.register(":SENSe#:AVERage:STATe", handler=self._handle_avg_state)
        t.register(":SENSe#:AVERage:COUNt", query_handler=self._handle_avg_count)

        # Source power
        t.register(":SOURce#:POWer", handler=self._handle_src_power)

        # Display — scale
        t.register(":DISPlay:WINDow#:TRACe#:Y:SCALe:RLEVel",
                   handler=self._handle_disp_rlevel)
        t.register(":DISPlay:WINDow#:TRACe#:Y:SCALe:PDIVision",
                   handler=self._handle_disp_pdiv)
        t.register(":DISPlay:WINDow#:TRACe#:Y:SCALe:RPOSition",
                   handler=self._handle_disp_rpos)

        # Display — channel/trace lists
        t.register(":DISPlay:CHANnel:LIST", query_handler=self._handle_chan_list)
        t.register(":DISPlay:TRACe:LIST", query_handler=self._handle_trace_list)
        t.register(":DISPlay:CHANnel#:TRACe:LIST",
                   query_handler=self._handle_chan_trace_list)

        # Display — create / activate
        t.register(":DISPlay:ADD:FUNCtion:EXECute",
                   set_handler=self._handle_add_function)
        t.register(":DISPlay:CHANnel#:ACTivate",
                   set_handler=self._handle_chan_activate)
        t.register(":DISPlay:TRACe#:ACTivate",
                   set_handler=self._handle_trace_activate)

        # Trigger / Initiate
        t.register(":INITiate#:CONTinuous", set_handler=self._handle_init_cont)
        t.register(":TRIGger:SCOPe", set_handler=self._handle_trig_scope)
        t.register(":TRIGger:SEQuence:SOURce", set_handler=self._handle_trig_src)
        t.register(":TRIGger:SEQuence:SING", set_handler=self._handle_trig_sing)

        # Correction
        t.register(":SENSe#:CORRection:STATe", handler=self._handle_corr_state)
        t.register(":SENSe#:CORRection:COEFficient:DATA",
                   handler=self._handle_corr_coef_data)
        t.register(":SENSe#:CORRection:COEFficient:SAVE",
                   set_handler=self._handle_corr_coef_save)
        t.register(":SENSe#:CORRection:COEFficient:METHod:RESPonse:OPEN",
                   set_handler=self._handle_corr_meth)
        t.register(":SENSe#:CORRection:COEFficient:METHod:RESPonse:SHORt",
                   set_handler=self._handle_corr_meth)
        t.register(":SENSe#:CORRection:COEFficient:METHod:RESPonse:THRU",
                   set_handler=self._handle_corr_meth)
        t.register(":SENSe#:CORRection:COEFficient:METHod:ERESponse",
                   set_handler=self._handle_corr_meth)
        t.register(":SENSe#:CORRection:COEFficient:METHod:SOLT#",
                   set_handler=self._handle_corr_meth)

        # Segment sweep
        t.register(":SENSe#:SEGMent:DATA", handler=self._handle_seg_data)
