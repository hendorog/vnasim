"""Proxy VNA model — presents one dialect, delegates to a real backend VNA.

``ProxyVNAModel`` replaces synthetic data generation with real
instrument communication.  The frontend SCPI tree (same mixins as
synthetic models) parses client commands; overridden handlers
translate them via a :class:`~vnasim.backend.translator.SNA5000Translator`
and forward to a :class:`~vnasim.backend.client.BackendClient`.
"""

from __future__ import annotations

import logging

from vnasim.backend.client import BackendClient
from vnasim.backend.translator import SNA5000Translator
from vnasim.models.common import CommonVNAModel, TraceState
from vnasim.scpi.types import ParsedCommand

logger = logging.getLogger(__name__)


class ProxyVNAModel(CommonVNAModel):
    """VNA model that proxies data-path operations to a real backend.

    Display/bookkeeping operations stay local.  Stimulus configuration,
    sweep control, and data reads are forwarded to the backend via the
    translator.  All frontend channels map to backend channel 1.
    """

    # Cyclomatic complexity: 1
    def __init__(
        self,
        *,
        num_ports: int = 2,
        idn: str = "",
        backend: BackendClient,
        translator: SNA5000Translator,
    ) -> None:
        self._backend = backend
        self._xlat = translator
        super().__init__(num_ports=num_ports, idn=idn)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    # Backend only has channel 1.  Frontend channels > 1 are probes
    # from drivers discovering multi-channel support — handle locally.
    _BACKEND_CHANNELS = {1}

    # Cyclomatic complexity: 2
    def _backend_ch(self, frontend_ch: int) -> int | None:
        """Map frontend channel to backend channel, or None if local-only."""
        return 1 if frontend_ch in self._BACKEND_CHANNELS else None

    # Cyclomatic complexity: 1
    def _backend_query(self, scpi: str) -> str:
        return self._backend.query(scpi)

    # Cyclomatic complexity: 1
    def _backend_write(self, scpi: str) -> None:
        self._backend.write(scpi)

    # Cyclomatic complexity: 2
    def _backend_trigger(self, ch: int) -> None:
        """Trigger a sweep on the backend and wait for completion."""
        bch = self._backend_ch(ch)
        if bch is None:
            return
        for cmd in self._xlat.trigger_sweep(bch):
            self._backend_write(cmd)
        self._backend_query("*OPC?")

    # Cyclomatic complexity: 2
    def _backend_set_measurement(self, ch: int, param: str) -> None:
        """Configure a measurement on the backend."""
        bch = self._backend_ch(ch)
        if bch is None:
            return
        for cmd in self._xlat.set_measurement(bch, 1, param):
            self._backend_write(cmd)

    # Cyclomatic complexity: 1
    def _find_active_trace(self, ch: int) -> TraceState:
        return self._selected_trace_for_channel(ch)

    # ------------------------------------------------------------------
    # Overridden handlers — forwarded to backend
    # ------------------------------------------------------------------

    # -- Frequency --

    # Cyclomatic complexity: 3
    def _handle_freq_start(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_freq_start(cmd)
        if cmd.is_query:
            resp = self._backend_query(self._xlat.query_freq_start(bch))
            self._ch(cmd).start_freq = float(resp)
            return resp
        val = float(cmd.arguments)
        self._backend_write(self._xlat.set_freq_start(bch, val))
        self._ch(cmd).start_freq = val
        return None

    # Cyclomatic complexity: 3
    def _handle_freq_stop(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_freq_stop(cmd)
        if cmd.is_query:
            resp = self._backend_query(self._xlat.query_freq_stop(bch))
            self._ch(cmd).stop_freq = float(resp)
            return resp
        val = float(cmd.arguments)
        self._backend_write(self._xlat.set_freq_stop(bch, val))
        self._ch(cmd).stop_freq = val
        return None

    # Cyclomatic complexity: 3
    def _handle_freq_cw(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_freq_cw(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_freq_cw(bch))
        self._backend_write(self._xlat.set_freq_cw(bch, float(cmd.arguments)))
        return None

    # Cyclomatic complexity: 2
    def _handle_freq_data(self, cmd: ParsedCommand) -> str:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_freq_data(cmd)
        return self._backend_query(self._xlat.query_freq_data(bch))

    # -- Sweep --

    # Cyclomatic complexity: 3
    def _handle_swp_points(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_swp_points(cmd)
        if cmd.is_query:
            resp = self._backend_query(self._xlat.query_swp_points(bch))
            self._ch(cmd).num_points = int(resp)
            return resp
        val = int(float(cmd.arguments))
        self._backend_write(self._xlat.set_swp_points(bch, val))
        self._ch(cmd).num_points = val
        return None

    # Cyclomatic complexity: 3
    def _handle_swp_type(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_swp_type(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_swp_type(bch))
        self._backend_write(self._xlat.set_swp_type(bch, cmd.arguments.strip()))
        return None

    # Cyclomatic complexity: 3
    def _handle_swp_time(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_swp_time(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_swp_time(bch))
        return None

    # -- IFBW --

    # Cyclomatic complexity: 3
    def _handle_ifbw(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_ifbw(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_ifbw(bch))
        self._backend_write(self._xlat.set_ifbw(bch, float(cmd.arguments)))
        return None

    # -- Power --

    # Cyclomatic complexity: 3
    def _handle_src_power(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_src_power(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_power(bch))
        self._backend_write(self._xlat.set_power(bch, float(cmd.arguments)))
        return None

    # -- Averaging --

    # Cyclomatic complexity: 3
    def _handle_avg_state(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_avg_state(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_avg_state(bch))
        self._backend_write(self._xlat.set_avg_state(bch, cmd.arguments.strip()))
        return None

    # Cyclomatic complexity: 3
    def _handle_smooth_state(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_smooth_state(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_smooth_state(bch))
        self._backend_write(self._xlat.set_smooth_state(bch, cmd.arguments.strip()))
        return None

    # Cyclomatic complexity: 3
    def _handle_smooth_aperture(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_smooth_aperture(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_smooth_aperture(bch))
        self._backend_write(
            self._xlat.set_smooth_aperture(bch, float(cmd.arguments))
        )
        return None

    # -- Correction --

    # Cyclomatic complexity: 3
    def _handle_corr_state(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_corr_state(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_corr_state(bch))
        self._backend_write(self._xlat.set_corr_state(bch, cmd.arguments.strip()))
        return None

    # Cyclomatic complexity: 3
    def _handle_corr_coef_data(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_corr_coef_data(cmd)
        if cmd.is_query:
            return self._backend_query(
                self._xlat.query_corr_coef(bch, cmd.arguments.strip())
            )
        self._backend_write(
            self._xlat.set_corr_coef(bch, cmd.arguments.strip())
        )
        return None

    # -- Segment data --

    # Cyclomatic complexity: 3
    def _handle_seg_data(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_seg_data(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_seg_data(bch))
        self._backend_write(self._xlat.set_seg_data(bch, cmd.arguments.strip()))
        return None

    # -- Data reads (the core value of the proxy) --

    # Cyclomatic complexity: 2
    def _handle_calc_sel_sdata(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        bch = self._backend_ch(ch)
        if bch is None:
            return super()._handle_calc_sel_sdata(cmd)
        tr_state = self._find_active_trace(ch)
        param = tr_state.parameter.upper()
        self._backend_set_measurement(ch, param)
        self._backend_trigger(ch)
        return self._backend_query(self._xlat.query_sdata(bch, param))

    # Cyclomatic complexity: 2
    def _handle_calc_sel_fdata(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        bch = self._backend_ch(ch)
        if bch is None:
            return super()._handle_calc_sel_fdata(cmd)
        tr_state = self._find_active_trace(ch)
        param = tr_state.parameter.upper()
        fmt = tr_state.format
        self._backend_set_measurement(ch, param)
        self._backend_write(self._xlat.set_trace_format(bch, fmt))
        self._backend_trigger(ch)
        return self._backend_query(self._xlat.query_selected_fdata(bch))

    # Cyclomatic complexity: 2
    def _handle_data_raw(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        bch = self._backend_ch(ch)
        if bch is None:
            return super()._handle_data_raw(cmd)
        param = cmd.arguments.strip().strip('"').upper()
        self._backend_set_measurement(ch, param)
        self._backend_trigger(ch)
        return self._backend_query(self._xlat.query_raw_data(bch, param))

    # Cyclomatic complexity: 2
    def _handle_data_corr(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        bch = self._backend_ch(ch)
        if bch is None:
            return super()._handle_data_corr(cmd)
        param = cmd.arguments.strip().strip('"').upper()
        self._backend_set_measurement(ch, param)
        self._backend_trigger(ch)
        return self._backend_query(self._xlat.query_sdata(bch, param))

    # -- Frequency center / span --

    # Cyclomatic complexity: 3
    def _handle_freq_center(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_freq_center(cmd)
        if cmd.is_query:
            resp = self._backend_query(self._xlat.query_freq_center(bch))
            sync_cmd = ParsedCommand(
                raw=cmd.raw,
                is_query=False,
                arguments=resp,
                suffixes=cmd.suffixes,
            )
            super()._handle_freq_center(sync_cmd)
            return resp
        self._backend_write(self._xlat.set_freq_center(bch, float(cmd.arguments)))
        super()._handle_freq_center(cmd)
        return None

    # Cyclomatic complexity: 3
    def _handle_freq_span(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_freq_span(cmd)
        if cmd.is_query:
            resp = self._backend_query(self._xlat.query_freq_span(bch))
            sync_cmd = ParsedCommand(
                raw=cmd.raw,
                is_query=False,
                arguments=resp,
                suffixes=cmd.suffixes,
            )
            super()._handle_freq_span(sync_cmd)
            return resp
        self._backend_write(self._xlat.set_freq_span(bch, float(cmd.arguments)))
        super()._handle_freq_span(cmd)
        return None

    # -- Sweep delay --

    # Cyclomatic complexity: 3
    def _handle_swp_delay(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_swp_delay(cmd)
        if cmd.is_query:
            resp = self._backend_query(self._xlat.query_swp_delay(bch))
            self._ch(cmd).sweep_delay = float(resp)
            return resp
        self._backend_write(
            self._xlat.set_swp_delay(bch, float(cmd.arguments))
        )
        super()._handle_swp_delay(cmd)
        return None

    # -- Averaging extras --

    # Cyclomatic complexity: 3
    def _handle_avg_count(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_avg_count(cmd)
        if cmd.is_query:
            resp = self._backend_query(self._xlat.query_avg_count(bch))
            self._ch(cmd).avg_count = int(float(resp))
            return resp
        self._backend_write(
            self._xlat.set_avg_count(bch, int(float(cmd.arguments)))
        )
        super()._handle_avg_count(cmd)
        return None

    # Cyclomatic complexity: 2
    def _handle_avg_clear(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return None
        self._backend_write(self._xlat.avg_clear(bch))
        return None

    # -- Electrical delay --

    # Cyclomatic complexity: 3
    def _handle_elec_delay(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_elec_delay(cmd)
        if cmd.is_query:
            resp = self._backend_query(self._xlat.query_elec_delay(bch))
            self._ch(cmd).elec_delay = float(resp)
            return resp
        self._backend_write(
            self._xlat.set_elec_delay(bch, float(cmd.arguments))
        )
        super()._handle_elec_delay(cmd)
        return None

    # -- Output state --

    # Cyclomatic complexity: 2
    def _handle_output(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            resp = self._backend_query(self._xlat.query_output())
            self._output_state = resp.strip().upper() in ("ON", "1")
            return resp
        self._backend_write(
            self._xlat.set_output(cmd.arguments.strip())
        )
        super()._handle_output(cmd)
        return None

    # -- Markers --

    # Cyclomatic complexity: 3
    def _handle_marker_state(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_marker_state(cmd)
        mk = cmd.trace
        if cmd.is_query:
            return self._backend_query(
                self._xlat.query_marker_state(bch, mk)
            )
        self._backend_write(
            self._xlat.set_marker_state(bch, mk, cmd.arguments.strip())
        )
        super()._handle_marker_state(cmd)
        return None

    # Cyclomatic complexity: 2
    def _handle_marker_activate(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_marker_activate(cmd)
        mk = cmd.trace
        self._backend_write(self._xlat.set_marker_activate(bch, mk))
        super()._handle_marker_activate(cmd)
        return None

    # Cyclomatic complexity: 3
    def _handle_marker_x(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_marker_x(cmd)
        mk = cmd.trace
        if cmd.is_query:
            return self._backend_query(self._xlat.query_marker_x(bch, mk))
        self._backend_write(
            self._xlat.set_marker_x(bch, mk, float(cmd.arguments))
        )
        super()._handle_marker_x(cmd)
        return None

    # Cyclomatic complexity: 2
    def _handle_marker_y(self, cmd: ParsedCommand) -> str:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_marker_y(cmd)
        mk = cmd.trace
        return self._backend_query(self._xlat.query_marker_y(bch, mk))

    # Cyclomatic complexity: 3
    def _handle_marker_func_type(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_marker_func_type(cmd)
        mk = cmd.trace
        if cmd.is_query:
            return self._backend_query(
                self._xlat.query_marker_func_type(bch, mk)
            )
        self._backend_write(
            self._xlat.set_marker_func_type(bch, mk, cmd.arguments.strip())
        )
        super()._handle_marker_func_type(cmd)
        return None

    # Cyclomatic complexity: 2
    def _handle_marker_func_exec(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_marker_func_exec(cmd)
        mk = cmd.trace
        self._backend_write(self._xlat.marker_func_exec(bch, mk))
        resp = self._backend_query(self._xlat.query_marker_x(bch, mk))
        sync_cmd = ParsedCommand(
            raw=cmd.raw,
            is_query=False,
            arguments=resp,
            suffixes=cmd.suffixes,
        )
        super()._handle_marker_x(sync_cmd)
        return None

    # Cyclomatic complexity: 3
    def _handle_marker_func_target(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_marker_func_target(cmd)
        mk = cmd.trace
        if cmd.is_query:
            return self._backend_query(
                self._xlat.query_marker_func_target(bch, mk)
            )
        self._backend_write(
            self._xlat.set_marker_func_target(bch, mk, float(cmd.arguments))
        )
        super()._handle_marker_func_target(cmd)
        return None

    # Cyclomatic complexity: 7
    def _handle_marker_set(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_marker_set(cmd)
        mk = cmd.trace
        action = cmd.arguments.strip().upper()
        if action.startswith("CENT"):
            self._backend_write(self._xlat.marker_set_center(bch, mk))
        elif action.startswith("STAR"):
            self._backend_write(self._xlat.marker_set_start(bch, mk))
        elif action.startswith("STOP"):
            self._backend_write(self._xlat.marker_set_stop(bch, mk))
        elif action.startswith("RLEV"):
            self._backend_write(self._xlat.marker_set_rlevel(bch, mk))
        elif action.startswith("DEL"):
            self._backend_write(self._xlat.marker_set_delay(bch, mk))
        super()._handle_marker_set(cmd)
        return None

    # Cyclomatic complexity: 2
    def _handle_marker_set_center(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_marker_set_center(cmd)
        self._backend_write(self._xlat.marker_set_center(bch, cmd.trace))
        super()._handle_marker_set_center(cmd)
        return None

    # Cyclomatic complexity: 2
    def _handle_marker_set_start(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_marker_set_start(cmd)
        self._backend_write(self._xlat.marker_set_start(bch, cmd.trace))
        super()._handle_marker_set_start(cmd)
        return None

    # Cyclomatic complexity: 2
    def _handle_marker_set_stop(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_marker_set_stop(cmd)
        self._backend_write(self._xlat.marker_set_stop(bch, cmd.trace))
        super()._handle_marker_set_stop(cmd)
        return None

    # -- Limit lines --

    # Cyclomatic complexity: 3
    def _handle_limit_state(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_limit_state(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_limit_state(bch))
        self._backend_write(
            self._xlat.set_limit_state(bch, cmd.arguments.strip())
        )
        return None

    # Cyclomatic complexity: 2
    def _handle_limit_fail(self, cmd: ParsedCommand) -> str:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_limit_fail(cmd)
        return self._backend_query(self._xlat.query_limit_fail(bch))

    # Cyclomatic complexity: 3
    def _handle_limit_data(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_limit_data(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_limit_data(bch))
        self._backend_write(
            self._xlat.set_limit_data(bch, cmd.arguments.strip())
        )
        return None

    # Cyclomatic complexity: 2
    def _handle_limit_clear(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_limit_clear(cmd)
        self._backend_write(self._xlat.limit_clear(bch))
        return None

    # -- Math / memory --

    # Cyclomatic complexity: 3
    def _handle_math_func(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_math_func(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_math_func(bch))
        self._backend_write(
            self._xlat.set_math_func(bch, cmd.arguments.strip())
        )
        return None

    # Cyclomatic complexity: 2
    def _handle_math_memorize(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_math_memorize(cmd)
        self._backend_write(self._xlat.math_memorize(bch))
        return None

    # -- Power extras --

    # Cyclomatic complexity: 3
    def _handle_src_port_power(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_src_port_power(cmd)
        port = cmd.trace
        if cmd.is_query:
            return self._backend_query(
                self._xlat.query_port_power(bch, port)
            )
        self._backend_write(
            self._xlat.set_port_power(bch, port, float(cmd.arguments))
        )
        return None

    # Cyclomatic complexity: 3
    def _handle_src_power_coupling(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_src_power_coupling(cmd)
        if cmd.is_query:
            return self._backend_query(
                self._xlat.query_power_coupling(bch)
            )
        self._backend_write(
            self._xlat.set_power_coupling(bch, cmd.arguments.strip())
        )
        return None

    # Cyclomatic complexity: 3
    def _handle_src_power_slope(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_src_power_slope(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_power_slope(bch))
        self._backend_write(
            self._xlat.set_power_slope(bch, float(cmd.arguments))
        )
        return None

    # Cyclomatic complexity: 3
    def _handle_src_power_slope_state(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_src_power_slope_state(cmd)
        if cmd.is_query:
            return self._backend_query(
                self._xlat.query_power_slope_state(bch)
            )
        self._backend_write(
            self._xlat.set_power_slope_state(bch, cmd.arguments.strip())
        )
        return None

    # Cyclomatic complexity: 3
    def _handle_src_power_start(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_src_power_start(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_power_start(bch))
        self._backend_write(
            self._xlat.set_power_start(bch, float(cmd.arguments))
        )
        return None

    # Cyclomatic complexity: 3
    def _handle_src_power_stop(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_src_power_stop(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_power_stop(bch))
        self._backend_write(
            self._xlat.set_power_stop(bch, float(cmd.arguments))
        )
        return None

    # -- Port extension --

    # Cyclomatic complexity: 3
    def _handle_port_ext_state(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_port_ext_state(cmd)
        if cmd.is_query:
            return self._backend_query(
                self._xlat.query_port_ext_state(bch)
            )
        self._backend_write(
            self._xlat.set_port_ext_state(bch, cmd.arguments.strip())
        )
        return None

    # Cyclomatic complexity: 3
    def _handle_port_ext_time(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_port_ext_time(cmd)
        port = cmd.trace
        if cmd.is_query:
            return self._backend_query(
                self._xlat.query_port_ext_time(bch, port)
            )
        self._backend_write(
            self._xlat.set_port_ext_time(bch, port, float(cmd.arguments))
        )
        return None

    # Cyclomatic complexity: 3
    def _handle_velocity_factor(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_velocity_factor(cmd)
        if cmd.is_query:
            return self._backend_query(
                self._xlat.query_velocity_factor(bch)
            )
        self._backend_write(
            self._xlat.set_velocity_factor(bch, float(cmd.arguments))
        )
        return None

    # Cyclomatic complexity: 3
    def _handle_impedance(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_impedance(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_impedance(bch))
        self._backend_write(
            self._xlat.set_impedance(bch, float(cmd.arguments))
        )
        return None
