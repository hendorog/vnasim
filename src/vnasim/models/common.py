"""Common VNA model — shared state, handlers, and core command registration.

All concrete VNA models inherit from this class. It provides:
- Channel and trace state management
- All handler methods (shared across models)
- Helper methods for data generation and formatting
- ``_register_core()`` for IEEE 488.2 and universal SCPI commands
"""

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
class MarkerState:
    state: bool = False
    x: float = 1e9
    discrete: bool = False
    func_type: str = "OFF"
    target: float = 0.0
    target_transition: str = "BOTH"
    tracking: bool = False
    domain_state: bool = False
    domain_start: float = 0.0
    domain_stop: float = 0.0
    bw_state: bool = False
    bw_threshold: float = -3.0


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
    # Sweep delay
    sweep_delay: float = 0.0
    # Averaging extras
    avg_type: str = "SWEep"
    # Electrical delay / phase offset
    elec_delay: float = 0.0
    phase_offset: float = 0.0
    # Markers
    markers: dict = field(default_factory=dict)
    marker_coupling: bool = False
    ref_marker_state: bool = False
    ref_marker_x: float = 1e9
    # Limit lines
    limit_state: bool = False
    limit_display: bool = False
    limit_data: str = ""
    limit_offset_ampl: float = 0.0
    limit_offset_stim: float = 0.0
    # Trace math
    math_func: str = "NORMal"
    # Port extension
    port_ext_state: bool = False
    port_ext_time: dict = field(default_factory=lambda: {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0})
    # Correction extras
    velocity_factor: float = 1.0
    impedance: float = 50.0
    # Power extras
    power_coupling: bool = True
    port_power: dict = field(default_factory=dict)
    power_slope: float = 0.0
    power_slope_state: bool = False
    power_start: float = -20.0
    power_stop: float = 0.0


@dataclass
class TraceState:
    channel: int = 1
    parameter: str = "S11"
    format: str = "MLOGarithmic"
    memory_sdata: object = None  # np.ndarray stored by MATH:MEM


class CommonVNAModel(VNAModel):
    """Base for all simulated VNA instruments.

    Provides state management and handler methods. Does NOT register
    any SCPI commands — subclasses call ``_register_core()`` and
    mixin registration methods in their ``_build_tree()``.
    """

    def __init__(self, *, num_ports: int = 2, idn: str = "") -> None:
        self._num_ports = num_ports
        self._idn = idn
        self._channels: dict[int, ChannelState] = {1: ChannelState()}
        self._traces: dict[int, TraceState] = {1: TraceState(channel=1)}
        self._active_channel = 1
        self._active_trace = 1
        self._next_channel = 2
        self._next_trace = 2
        self._trigger_scope = "ALL"
        self._trigger_source = "INTernal"
        self._trigger_point = False
        # IEEE 488.2 status registers
        self._ese: int = 0
        self._esr: int = 0
        self._sre: int = 0
        # RF output
        self._output_state = True
        self._tree = SCPITree()
        self._build_tree()

    @property
    def tree(self) -> SCPITree:
        return self._tree

    # ------------------------------------------------------------------
    # Core registration — truly universal commands
    # ------------------------------------------------------------------

    def _register_core(self) -> None:
        """Register IEEE 488.2, frequency, sweep, power, correction state."""
        t = self._tree

        # IEEE 488.2
        t.register("*IDN", query_handler=self._handle_idn)
        t.register("*RST", set_handler=self._handle_rst)
        t.register("*OPC", query_handler=self._handle_opc)
        t.register("*CLS", set_handler=self._handle_cls)
        t.register("*ESE", handler=self._handle_ese)
        t.register("*ESR", query_handler=self._handle_esr)
        t.register("*SRE", handler=self._handle_sre)
        t.register("*STB", query_handler=self._handle_stb)
        t.register("*WAI", set_handler=self._handle_wai)
        t.register("*TRG", set_handler=self._handle_trig_sing)

        # System
        t.register(":SYSTem:ERRor", query_handler=self._handle_sys_err)
        t.register(":SYSTem:PRESet", set_handler=self._handle_rst)
        t.register(":ABORt", set_handler=self._handle_abort)
        t.register(":OUTPut", handler=self._handle_output)

        # Frequency
        t.register(":SENSe#:FREQuency:STARt", handler=self._handle_freq_start)
        t.register(":SENSe#:FREQuency:STOP", handler=self._handle_freq_stop)
        t.register(":SENSe#:FREQuency:CENTer", handler=self._handle_freq_center)
        t.register(":SENSe#:FREQuency:SPAN", handler=self._handle_freq_span)
        t.register(":SENSe#:FREQuency:CW", handler=self._handle_freq_cw)

        # Sweep
        t.register(":SENSe#:SWEep:POINts", handler=self._handle_swp_points)
        t.register(":SENSe#:SWEep:TIME", handler=self._handle_swp_time)
        t.register(":SENSe#:SWEep:TIME:AUTO", set_handler=self._handle_swp_time_auto)
        t.register(":SENSe#:SWEep:DELay", handler=self._handle_swp_delay)

        # Source power (channel-level + per-port + extras)
        t.register(":SOURce#:POWer", handler=self._handle_src_power)
        t.register(":SOURce#:POWer:PORT#", handler=self._handle_src_port_power)
        t.register(":SOURce#:POWer:PORT:COUPle", handler=self._handle_src_power_coupling)
        t.register(":SOURce#:POWer:SLOPe", handler=self._handle_src_power_slope)
        t.register(":SOURce#:POWer:SLOPe:STATe", handler=self._handle_src_power_slope_state)
        t.register(":SOURce#:POWer:STARt", handler=self._handle_src_power_start)
        t.register(":SOURce#:POWer:STOP", handler=self._handle_src_power_stop)

        # Correction state + extras
        t.register(":SENSe#:CORRection:STATe", handler=self._handle_corr_state)
        t.register(":SENSe#:CORRection:EXTension:STATe",
                   handler=self._handle_port_ext_state)
        t.register(":SENSe#:CORRection:EXTension:PORT#:TIME",
                   handler=self._handle_port_ext_time)
        t.register(":SENSe#:CORRection:RVELocity:COAX",
                   handler=self._handle_velocity_factor)
        t.register(":SENSe#:CORRection:IMPedance",
                   handler=self._handle_impedance)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ch(self, cmd: ParsedCommand) -> ChannelState:
        ch = cmd.channel
        if ch not in self._channels:
            self._channels[ch] = ChannelState()
        return self._channels[ch]

    def _tr(self, cmd: ParsedCommand) -> TraceState:
        tr = cmd.trace
        if tr not in self._traces:
            self._traces[tr] = TraceState(channel=cmd.channel)
        return self._traces[tr]

    def _selected_trace_for_channel(self, ch: int) -> TraceState:
        """Return the selected trace for a channel, falling back sensibly."""
        active = self._traces.get(self._active_trace)
        if active is not None and active.channel == ch:
            return active
        for trace_num in sorted(self._traces):
            tr_state = self._traces[trace_num]
            if tr_state.channel == ch:
                return tr_state
        return TraceState(channel=ch)

    def _freq_grid(self, state: ChannelState) -> np.ndarray:
        return np.linspace(state.start_freq, state.stop_freq, state.num_points)

    def _format_complex(self, data: np.ndarray) -> str:
        parts: list[str] = []
        for c in data:
            parts.append(str(c.real))
            parts.append(str(c.imag))
        return ",".join(parts)

    def _generate_sdata(self, param: str, state: ChannelState) -> str:
        freqs = self._freq_grid(state)
        p = param.strip().strip('"').upper()
        if len(p) >= 3 and p[0] == 'S' and p[1:].isdigit():
            data = generate_param(p, freqs, self._num_ports)
        else:
            data = isolation_response(freqs, isolation_dB=-20.0)
        return self._format_complex(data)

    def _apply_format(self, data: np.ndarray, fmt: str) -> str:
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
        if term.upper() in ("ER", "ET", "ERFT", "ETRT", "REFLTRACK",
                            "TRANSTRACK", "ET11", "ET22", "ET21", "ET12"):
            return np.ones(n, dtype=complex)
        return np.zeros(n, dtype=complex)

    # ------------------------------------------------------------------
    # Handler methods — shared across all models
    # ------------------------------------------------------------------

    # IEEE 488.2
    def _handle_idn(self, cmd: ParsedCommand) -> str:
        return self._idn

    def _handle_rst(self, cmd: ParsedCommand) -> str | None:
        self._channels = {1: ChannelState()}
        self._traces = {1: TraceState(channel=1)}
        self._active_channel = 1
        self._active_trace = 1
        self._next_channel = 2
        self._next_trace = 2
        self._trigger_source = "INTernal"
        self._trigger_scope = "ALL"
        self._trigger_point = False
        self._output_state = True
        return None

    def _handle_opc(self, cmd: ParsedCommand) -> str:
        return "1"

    # Frequency
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

    # Sweep
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

    # IFBW (handler used by multiple registration paths)
    def _handle_ifbw(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.if_bw)
        state.if_bw = float(cmd.arguments)
        return None

    # Calculate — parameter / format / data
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
        if self._active_trace in self._traces:
            if cmd.is_query:
                return self._traces[self._active_trace].format
            self._traces[self._active_trace].format = cmd.arguments.strip()
        return None

    def _handle_calc_sel_fdata(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        state = self._ch(cmd)
        tr_state = self._selected_trace_for_channel(ch)
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
        tr_state = self._selected_trace_for_channel(ch)
        return self._generate_sdata(tr_state.parameter, state)

    def _handle_data_raw(self, cmd: ParsedCommand) -> str:
        return self._generate_sdata(cmd.arguments, self._ch(cmd))

    def _handle_data_corr(self, cmd: ParsedCommand) -> str:
        return self._generate_sdata(cmd.arguments, self._ch(cmd))

    # Averaging
    def _handle_avg_state(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return "ON" if state.avg_state else "OFF"
        state.avg_state = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    # Smoothing
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

    # Source power
    def _handle_src_power(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.power)
        state.power = float(cmd.arguments)
        return None

    # Display scale
    def _handle_disp_rlevel(self, cmd: ParsedCommand) -> str | None:
        ch_num = cmd.suffixes[0] if cmd.suffixes else self._active_channel
        if ch_num not in self._channels:
            self._channels[ch_num] = ChannelState()
        state = self._channels[ch_num]
        if cmd.is_query:
            return str(state.ref_level)
        state.ref_level = float(cmd.arguments)
        return None

    def _handle_disp_pdiv(self, cmd: ParsedCommand) -> str | None:
        ch_num = cmd.suffixes[0] if cmd.suffixes else self._active_channel
        if ch_num not in self._channels:
            self._channels[ch_num] = ChannelState()
        state = self._channels[ch_num]
        if cmd.is_query:
            return str(state.per_div)
        state.per_div = float(cmd.arguments)
        return None

    def _handle_disp_rpos(self, cmd: ParsedCommand) -> str | None:
        ch_num = cmd.suffixes[0] if cmd.suffixes else self._active_channel
        if ch_num not in self._channels:
            self._channels[ch_num] = ChannelState()
        state = self._channels[ch_num]
        if cmd.is_query:
            return str(state.ref_position)
        state.ref_position = int(float(cmd.arguments))
        return None

    # Display — channel / trace management
    def _handle_chan_list(self, cmd: ParsedCommand) -> str:
        return ",".join(str(ch) for ch in sorted(self._channels))

    def _handle_trace_list(self, cmd: ParsedCommand) -> str:
        return ",".join(str(tr) for tr in sorted(self._traces))

    def _handle_chan_trace_list(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        traces = [tr for tr, ts in sorted(self._traces.items()) if ts.channel == ch]
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
        tr = cmd.channel  # first suffix
        self._active_trace = tr
        if tr in self._traces:
            self._active_channel = self._traces[tr].channel
        return None

    # Trigger / Initiate
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
        return None

    def _handle_init_imm(self, cmd: ParsedCommand) -> str | None:
        return None

    # Balanced topology
    def _handle_dtopology(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return state.topology or "NONE"
        state.topology = cmd.arguments.strip()
        return None

    # Correction
    def _handle_corr_state(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return "ON" if state.corr_state else "OFF"
        state.corr_state = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_corr_coef_data(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            args = cmd.arguments.strip()
            n = state.num_points
            key = args.upper()
            if key in state.cal_coefficients:
                return self._format_complex(state.cal_coefficients[key])
            term = args.split(",")[0].strip().strip("'\"") if args else "ED"
            return self._format_complex(self._ideal_coef(term, n))
        args = cmd.arguments.strip()
        parts = args.split(",")
        if len(parts) >= 3:
            key = ",".join(parts[:3]).upper()
            vals = [float(x) for x in parts[3:]]
            data = np.array(vals[0::2]) + 1j * np.array(vals[1::2])
            state.cal_coefficients[key] = data
        return None

    def _handle_corr_coef_save(self, cmd: ParsedCommand) -> str | None:
        return None

    def _handle_corr_meth(self, cmd: ParsedCommand) -> str | None:
        return None

    # Segment data (bulk format)
    def _handle_seg_data(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return state.segment_data or "5,0,0,0,0,0,0"
        state.segment_data = cmd.arguments.strip()
        return None

    # ------------------------------------------------------------------
    # IEEE 488.2 status / system
    # ------------------------------------------------------------------

    def _handle_cls(self, cmd: ParsedCommand) -> str | None:
        self._esr = 0
        return None

    def _handle_ese(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            return str(self._ese)
        self._ese = int(float(cmd.arguments))
        return None

    def _handle_esr(self, cmd: ParsedCommand) -> str:
        val = self._esr
        self._esr = 0
        return str(val)

    def _handle_sre(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            return str(self._sre)
        self._sre = int(float(cmd.arguments))
        return None

    def _handle_stb(self, cmd: ParsedCommand) -> str:
        return "0"

    def _handle_wai(self, cmd: ParsedCommand) -> str | None:
        return None

    def _handle_sys_err(self, cmd: ParsedCommand) -> str:
        return '0,"No error"'

    def _handle_abort(self, cmd: ParsedCommand) -> str | None:
        return None

    # ------------------------------------------------------------------
    # Output state (RF on/off)
    # ------------------------------------------------------------------

    def _handle_output(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            return "1" if self._output_state else "0"
        self._output_state = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    # ------------------------------------------------------------------
    # Frequency center / span (computed from start/stop)
    # ------------------------------------------------------------------

    def _handle_freq_center(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str((state.start_freq + state.stop_freq) / 2.0)
        center = float(cmd.arguments)
        span = state.stop_freq - state.start_freq
        state.start_freq = center - span / 2.0
        state.stop_freq = center + span / 2.0
        return None

    def _handle_freq_span(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.stop_freq - state.start_freq)
        span = float(cmd.arguments)
        center = (state.start_freq + state.stop_freq) / 2.0
        state.start_freq = center - span / 2.0
        state.stop_freq = center + span / 2.0
        return None

    # ------------------------------------------------------------------
    # Sweep delay
    # ------------------------------------------------------------------

    def _handle_swp_delay(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.sweep_delay)
        state.sweep_delay = float(cmd.arguments)
        return None

    # ------------------------------------------------------------------
    # Averaging enhancements
    # ------------------------------------------------------------------

    def _handle_avg_count(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.avg_count)
        state.avg_count = int(float(cmd.arguments))
        return None

    def _handle_avg_clear(self, cmd: ParsedCommand) -> str | None:
        return None

    def _handle_avg_type(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return state.avg_type
        state.avg_type = cmd.arguments.strip()
        return None

    # ------------------------------------------------------------------
    # Electrical delay / phase offset
    # ------------------------------------------------------------------

    def _handle_elec_delay(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.elec_delay)
        state.elec_delay = float(cmd.arguments)
        return None

    def _handle_phase_offset(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.phase_offset)
        state.phase_offset = float(cmd.arguments)
        return None

    # ------------------------------------------------------------------
    # Markers
    # ------------------------------------------------------------------

    def _mk(self, cmd: ParsedCommand) -> MarkerState:
        """Get or create marker state for this channel + marker number."""
        state = self._ch(cmd)
        mk = cmd.trace  # second suffix = marker number
        if mk not in state.markers:
            state.markers[mk] = MarkerState()
        return state.markers[mk]

    def _marker_y_at(self, ch: int, x: float) -> str:
        """Compute marker Y value at stimulus *x* for the active trace."""
        state = self._channels.get(ch, ChannelState())
        tr_state = self._selected_trace_for_channel(ch)
        freqs = self._freq_grid(state)
        param = tr_state.parameter.strip().strip('"').upper()
        if len(param) >= 3 and param[0] == 'S' and param[1:].isdigit():
            data = generate_param(param, freqs, self._num_ports)
        else:
            data = isolation_response(freqs, isolation_dB=-20.0)
        idx = int(np.argmin(np.abs(freqs - x)))
        c = data[idx]
        fmt = tr_state.format.upper()
        if fmt.startswith("MLOG"):
            val = 20.0 * np.log10(max(abs(c), 1e-15))
            return f"{val},0"
        elif fmt.startswith("PHAS") or fmt.startswith("UPH"):
            return f"{np.degrees(np.angle(c))},0"
        elif fmt.startswith("MLIN"):
            return f"{abs(c)},0"
        elif fmt == "SWR":
            r = min(abs(c), 0.9999)
            return f"{(1 + r) / (1 - r)},0"
        elif fmt == "REAL":
            return f"{c.real},0"
        elif fmt.startswith("IMAG"):
            return f"0,{c.imag}"
        elif fmt.startswith("GDEL"):
            return "0,0"
        else:
            return f"{c.real},{c.imag}"

    def _marker_search(self, ch: int, mk_state: MarkerState) -> None:
        """Execute marker search, updating mk_state.x."""
        state = self._channels.get(ch, ChannelState())
        tr_state = self._selected_trace_for_channel(ch)
        freqs = self._freq_grid(state)
        param = tr_state.parameter.strip().strip('"').upper()
        if len(param) >= 3 and param[0] == 'S' and param[1:].isdigit():
            data = generate_param(param, freqs, self._num_ports)
        else:
            data = isolation_response(freqs, isolation_dB=-20.0)
        # Compute scalar magnitude (dB) for search
        mag = 20.0 * np.log10(np.maximum(np.abs(data), 1e-15))
        # Apply search domain if enabled
        mask = np.ones(len(freqs), dtype=bool)
        if mk_state.domain_state:
            mask = (freqs >= mk_state.domain_start) & (freqs <= mk_state.domain_stop)
        if not np.any(mask):
            return
        func = mk_state.func_type.upper()
        if func.startswith("MAX"):
            idx = np.argmax(np.where(mask, mag, -np.inf))
        elif func.startswith("MIN"):
            idx = np.argmin(np.where(mask, mag, np.inf))
        elif func.startswith("PEAK") or func.startswith("RPEAK") or func.startswith("LPEAK"):
            idx = np.argmax(np.where(mask, mag, -np.inf))
        elif func.startswith("TARG"):
            target = mk_state.target
            diffs = np.abs(mag - target)
            diffs = np.where(mask, diffs, np.inf)
            idx = np.argmin(diffs)
        else:
            return
        mk_state.x = float(freqs[int(idx)])

    def _handle_marker_state(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        if cmd.is_query:
            return "1" if ms.state else "0"
        ms.state = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_marker_activate(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        ms.state = True
        return None

    def _handle_marker_x(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        if cmd.is_query:
            return str(ms.x)
        ms.x = float(cmd.arguments)
        return None

    def _handle_marker_y(self, cmd: ParsedCommand) -> str:
        ms = self._mk(cmd)
        return self._marker_y_at(cmd.channel, ms.x)

    def _handle_marker_discrete(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        if cmd.is_query:
            return "1" if ms.discrete else "0"
        ms.discrete = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_marker_coupling(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return "1" if state.marker_coupling else "0"
        state.marker_coupling = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_marker_ref_state(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return "1" if state.ref_marker_state else "0"
        state.ref_marker_state = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_marker_ref_x(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.ref_marker_x)
        state.ref_marker_x = float(cmd.arguments)
        return None

    def _handle_marker_ref_y(self, cmd: ParsedCommand) -> str:
        state = self._ch(cmd)
        return self._marker_y_at(cmd.channel, state.ref_marker_x)

    def _handle_marker_func_type(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        if cmd.is_query:
            return ms.func_type
        ms.func_type = cmd.arguments.strip()
        return None

    def _handle_marker_func_exec(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        self._marker_search(cmd.channel, ms)
        return None

    def _handle_marker_func_target(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        if cmd.is_query:
            return str(ms.target)
        ms.target = float(cmd.arguments)
        return None

    def _handle_marker_func_ttrans(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        if cmd.is_query:
            return ms.target_transition
        ms.target_transition = cmd.arguments.strip()
        return None

    def _handle_marker_func_tracking(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        if cmd.is_query:
            return "1" if ms.tracking else "0"
        ms.tracking = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_marker_func_domain_state(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        if cmd.is_query:
            return "1" if ms.domain_state else "0"
        ms.domain_state = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_marker_func_domain_start(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        if cmd.is_query:
            return str(ms.domain_start)
        ms.domain_start = float(cmd.arguments)
        return None

    def _handle_marker_func_domain_stop(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        if cmd.is_query:
            return str(ms.domain_stop)
        ms.domain_stop = float(cmd.arguments)
        return None

    def _handle_marker_bw_state(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        if cmd.is_query:
            return "1" if ms.bw_state else "0"
        ms.bw_state = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_marker_bw_data(self, cmd: ParsedCommand) -> str:
        """Return bandwidth search result: bw,center,q,loss."""
        ms = self._mk(cmd)
        state = self._ch(cmd)
        tr_state = self._selected_trace_for_channel(cmd.channel)
        freqs = self._freq_grid(state)
        param = tr_state.parameter.strip().strip('"').upper()
        if len(param) >= 3 and param[0] == 'S' and param[1:].isdigit():
            data = generate_param(param, freqs, self._num_ports)
        else:
            data = isolation_response(freqs, isolation_dB=-20.0)
        mag = 20.0 * np.log10(np.maximum(np.abs(data), 1e-15))
        peak_idx = int(np.argmax(mag))
        peak_val = mag[peak_idx]
        threshold = peak_val + ms.bw_threshold
        above = mag >= threshold
        indices = np.where(above)[0]
        if len(indices) >= 2:
            f_low = float(freqs[indices[0]])
            f_high = float(freqs[indices[-1]])
        else:
            f_low = float(freqs[peak_idx])
            f_high = float(freqs[peak_idx])
        bw = f_high - f_low
        center = (f_low + f_high) / 2.0
        q = center / bw if bw > 0 else 0.0
        loss = float(peak_val)
        return f"{bw},{center},{q},{loss}"

    def _handle_marker_bw_threshold(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        if cmd.is_query:
            return str(ms.bw_threshold)
        ms.bw_threshold = float(cmd.arguments)
        return None

    def _handle_marker_set(self, cmd: ParsedCommand) -> str | None:
        """Marker→ action. E5071B sends :CALC:MARK:SET with argument."""
        ms = self._mk(cmd)
        action = cmd.arguments.strip().upper()
        state = self._ch(cmd)
        if action.startswith("CENT"):
            span = state.stop_freq - state.start_freq
            state.start_freq = ms.x - span / 2.0
            state.stop_freq = ms.x + span / 2.0
        elif action.startswith("STAR"):
            state.start_freq = ms.x
        elif action.startswith("STOP"):
            state.stop_freq = ms.x
        elif action.startswith("RLEV"):
            y = self._marker_y_at(cmd.channel, ms.x)
            state.ref_level = float(y.split(",")[0])
        elif action.startswith("DEL"):
            state.elec_delay = 0.0  # simplified
        return None

    def _handle_marker_set_center(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        state = self._ch(cmd)
        span = state.stop_freq - state.start_freq
        state.start_freq = ms.x - span / 2.0
        state.stop_freq = ms.x + span / 2.0
        return None

    def _handle_marker_set_start(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        self._ch(cmd).start_freq = ms.x
        return None

    def _handle_marker_set_stop(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        self._ch(cmd).stop_freq = ms.x
        return None

    def _handle_marker_set_rlevel(self, cmd: ParsedCommand) -> str | None:
        ms = self._mk(cmd)
        y = self._marker_y_at(cmd.channel, ms.x)
        self._ch(cmd).ref_level = float(y.split(",")[0])
        return None

    def _handle_marker_set_delay(self, cmd: ParsedCommand) -> str | None:
        return None

    # ------------------------------------------------------------------
    # Limit lines
    # ------------------------------------------------------------------

    def _handle_limit_state(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return "1" if state.limit_state else "0"
        state.limit_state = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_limit_display(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return "1" if state.limit_display else "0"
        state.limit_display = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_limit_fail(self, cmd: ParsedCommand) -> str:
        return "0"  # always pass in simulation

    def _handle_limit_data(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return state.limit_data or "0"
        state.limit_data = cmd.arguments.strip()
        return None

    def _handle_limit_clear(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        state.limit_data = ""
        state.limit_state = False
        return None

    def _handle_limit_offset_ampl(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.limit_offset_ampl)
        state.limit_offset_ampl = float(cmd.arguments)
        return None

    def _handle_limit_offset_stim(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.limit_offset_stim)
        state.limit_offset_stim = float(cmd.arguments)
        return None

    def _handle_limit_report_all(self, cmd: ParsedCommand) -> str:
        state = self._ch(cmd)
        return ",".join(["0"] * state.num_points)

    def _handle_limit_report_data(self, cmd: ParsedCommand) -> str:
        return "0"

    def _handle_limit_report_points(self, cmd: ParsedCommand) -> str:
        return "0"

    # ------------------------------------------------------------------
    # Trace math / memory
    # ------------------------------------------------------------------

    def _handle_math_func(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return state.math_func
        state.math_func = cmd.arguments.strip()
        return None

    def _handle_math_memorize(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        state = self._ch(cmd)
        tr_state = self._selected_trace_for_channel(ch)
        freqs = self._freq_grid(state)
        param = tr_state.parameter.strip().strip('"').upper()
        if len(param) >= 3 and param[0] == 'S' and param[1:].isdigit():
            tr_state.memory_sdata = generate_param(param, freqs, self._num_ports)
        else:
            tr_state.memory_sdata = isolation_response(freqs, isolation_dB=-20.0)
        return None

    def _handle_data_fmem(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        tr_state = self._selected_trace_for_channel(ch)
        if tr_state is None or tr_state.memory_sdata is None:
            state = self._ch(cmd)
            return ",".join(["0"] * state.num_points * 2)
        return self._apply_format(tr_state.memory_sdata, tr_state.format)

    def _handle_data_smem(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        tr_state = self._selected_trace_for_channel(ch)
        if tr_state is None or tr_state.memory_sdata is None:
            state = self._ch(cmd)
            return ",".join(["0"] * state.num_points * 2)
        return self._format_complex(tr_state.memory_sdata)

    def _handle_math_stats_state(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            return "0"
        return None

    def _handle_math_stats_data(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        state = self._ch(cmd)
        tr_state = self._selected_trace_for_channel(ch)
        freqs = self._freq_grid(state)
        param = tr_state.parameter.strip().strip('"').upper()
        if len(param) >= 3 and param[0] == 'S' and param[1:].isdigit():
            data = generate_param(param, freqs, self._num_ports)
        else:
            data = isolation_response(freqs, isolation_dB=-20.0)
        mag = 20.0 * np.log10(np.maximum(np.abs(data), 1e-15))
        mean_val = float(np.mean(mag))
        std_val = float(np.std(mag))
        pk_pk = float(np.max(mag) - np.min(mag))
        return f"{mean_val},{std_val},{pk_pk}"

    # ------------------------------------------------------------------
    # Source power extras
    # ------------------------------------------------------------------

    def _handle_src_port_power(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        port = cmd.trace  # second suffix = port number
        if cmd.is_query:
            return str(state.port_power.get(port, state.power))
        state.port_power[port] = float(cmd.arguments)
        return None

    def _handle_src_power_coupling(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return "1" if state.power_coupling else "0"
        state.power_coupling = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_src_power_slope(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.power_slope)
        state.power_slope = float(cmd.arguments)
        return None

    def _handle_src_power_slope_state(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return "1" if state.power_slope_state else "0"
        state.power_slope_state = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_src_power_start(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.power_start)
        state.power_start = float(cmd.arguments)
        return None

    def _handle_src_power_stop(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.power_stop)
        state.power_stop = float(cmd.arguments)
        return None

    # ------------------------------------------------------------------
    # Port extension / velocity / impedance
    # ------------------------------------------------------------------

    def _handle_port_ext_state(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return "1" if state.port_ext_state else "0"
        state.port_ext_state = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_port_ext_time(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        port = cmd.trace  # second suffix = port number
        if cmd.is_query:
            return str(state.port_ext_time.get(port, 0.0))
        state.port_ext_time[port] = float(cmd.arguments)
        return None

    def _handle_velocity_factor(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.velocity_factor)
        state.velocity_factor = float(cmd.arguments)
        return None

    def _handle_impedance(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            return str(state.impedance)
        state.impedance = float(cmd.arguments)
        return None

    # ------------------------------------------------------------------
    # Trigger extras
    # ------------------------------------------------------------------

    def _handle_trig_point(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            return "1" if self._trigger_point else "0"
        self._trigger_point = cmd.arguments.strip().upper() in ("ON", "1")
        return None

    def _handle_trig_src_query(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            return self._trigger_source
        self._trigger_source = cmd.arguments.strip()
        return None

    # ------------------------------------------------------------------
    # Display auto scale
    # ------------------------------------------------------------------

    def _handle_disp_auto_scale(self, cmd: ParsedCommand) -> str | None:
        return None
