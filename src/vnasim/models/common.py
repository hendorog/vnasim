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

        # Frequency
        t.register(":SENSe#:FREQuency:STARt", handler=self._handle_freq_start)
        t.register(":SENSe#:FREQuency:STOP", handler=self._handle_freq_stop)
        t.register(":SENSe#:FREQuency:CW", handler=self._handle_freq_cw)

        # Sweep
        t.register(":SENSe#:SWEep:POINts", handler=self._handle_swp_points)
        t.register(":SENSe#:SWEep:TIME", handler=self._handle_swp_time)
        t.register(":SENSe#:SWEep:TIME:AUTO", set_handler=self._handle_swp_time_auto)

        # Source power
        t.register(":SOURce#:POWer", handler=self._handle_src_power)

        # Correction state
        t.register(":SENSe#:CORRection:STATe", handler=self._handle_corr_state)

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

    def _handle_avg_count(self, cmd: ParsedCommand) -> str:
        return str(self._ch(cmd).avg_count)

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
