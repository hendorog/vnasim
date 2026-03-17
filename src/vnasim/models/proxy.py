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
from vnasim.models.common import CommonVNAModel
from vnasim.scpi.types import ParsedCommand

logger = logging.getLogger(__name__)


class ProxyVNAModel(CommonVNAModel):
    """VNA model that proxies data-path operations to a real backend.

    Display/bookkeeping operations stay local.  Stimulus configuration,
    sweep control, and data reads are forwarded to the backend via the
    translator.
    """

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

    def _backend_query(self, scpi: str) -> str:
        """Send a query to the backend and return the response."""
        return self._backend.query(scpi)

    def _backend_write(self, scpi: str) -> None:
        """Send a write command to the backend."""
        self._backend.write(scpi)

    def _backend_trigger(self, ch: int) -> None:
        """Trigger a sweep on the backend and wait for completion."""
        for cmd in self._xlat.trigger_sweep(ch):
            self._backend_write(cmd)
        self._backend_query("*OPC?")

    def _backend_set_measurement(self, ch: int, param: str) -> None:
        """Configure a measurement on the backend."""
        for cmd in self._xlat.set_measurement(ch, 1, param):
            self._backend_write(cmd)

    # ------------------------------------------------------------------
    # Overridden handlers — forwarded to backend
    # ------------------------------------------------------------------

    # -- Frequency --

    def _handle_freq_start(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if cmd.is_query:
            resp = self._backend_query(self._xlat.query_freq_start(ch))
            self._ch(cmd).start_freq = float(resp)
            return resp
        val = float(cmd.arguments)
        self._backend_write(self._xlat.set_freq_start(ch, val))
        self._ch(cmd).start_freq = val
        return None

    def _handle_freq_stop(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if cmd.is_query:
            resp = self._backend_query(self._xlat.query_freq_stop(ch))
            self._ch(cmd).stop_freq = float(resp)
            return resp
        val = float(cmd.arguments)
        self._backend_write(self._xlat.set_freq_stop(ch, val))
        self._ch(cmd).stop_freq = val
        return None

    def _handle_freq_cw(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if cmd.is_query:
            return self._backend_query(self._xlat.query_freq_cw(ch))
        self._backend_write(self._xlat.set_freq_cw(ch, float(cmd.arguments)))
        return None

    def _handle_freq_data(self, cmd: ParsedCommand) -> str:
        return self._backend_query(self._xlat.query_freq_data(cmd.channel))

    # -- Sweep --

    def _handle_swp_points(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if cmd.is_query:
            resp = self._backend_query(self._xlat.query_swp_points(ch))
            self._ch(cmd).num_points = int(resp)
            return resp
        val = int(float(cmd.arguments))
        self._backend_write(self._xlat.set_swp_points(ch, val))
        self._ch(cmd).num_points = val
        return None

    def _handle_swp_type(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if cmd.is_query:
            return self._backend_query(self._xlat.query_swp_type(ch))
        self._backend_write(self._xlat.set_swp_type(ch, cmd.arguments.strip()))
        return None

    def _handle_swp_time(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            return self._backend_query(self._xlat.query_swp_time(cmd.channel))
        return None  # sweep time is read-only on most backends

    # -- IFBW --

    def _handle_ifbw(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if cmd.is_query:
            return self._backend_query(self._xlat.query_ifbw(ch))
        self._backend_write(self._xlat.set_ifbw(ch, float(cmd.arguments)))
        return None

    # -- Power --

    def _handle_src_power(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if cmd.is_query:
            return self._backend_query(self._xlat.query_power(ch))
        self._backend_write(self._xlat.set_power(ch, float(cmd.arguments)))
        return None

    # -- Averaging --

    def _handle_avg_state(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if cmd.is_query:
            return self._backend_query(self._xlat.query_avg_state(ch))
        self._backend_write(self._xlat.set_avg_state(ch, cmd.arguments.strip()))
        return None

    def _handle_avg_count(self, cmd: ParsedCommand) -> str:
        return self._backend_query(self._xlat.query_avg_count(cmd.channel))

    # -- Smoothing --

    def _handle_smooth_state(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if cmd.is_query:
            return self._backend_query(self._xlat.query_smooth_state(ch))
        self._backend_write(self._xlat.set_smooth_state(ch, cmd.arguments.strip()))
        return None

    def _handle_smooth_aperture(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if cmd.is_query:
            return self._backend_query(self._xlat.query_smooth_aperture(ch))
        self._backend_write(
            self._xlat.set_smooth_aperture(ch, float(cmd.arguments))
        )
        return None

    # -- Correction --

    def _handle_corr_state(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if cmd.is_query:
            return self._backend_query(self._xlat.query_corr_state(ch))
        self._backend_write(self._xlat.set_corr_state(ch, cmd.arguments.strip()))
        return None

    def _handle_corr_coef_data(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if cmd.is_query:
            return self._backend_query(
                self._xlat.query_corr_coef(ch, cmd.arguments.strip())
            )
        self._backend_write(
            self._xlat.set_corr_coef(ch, cmd.arguments.strip())
        )
        return None

    # -- Segment data --

    def _handle_seg_data(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if cmd.is_query:
            return self._backend_query(self._xlat.query_seg_data(ch))
        self._backend_write(self._xlat.set_seg_data(ch, cmd.arguments.strip()))
        return None

    # -- Data reads (the core value of the proxy) --

    def _handle_calc_sel_sdata(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        tr_state = self._find_active_trace(ch)
        param = tr_state.parameter.upper()
        self._backend_set_measurement(ch, param)
        self._backend_trigger(ch)
        return self._backend_query(self._xlat.query_sdata(ch, param))

    def _handle_calc_sel_fdata(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        tr_state = self._find_active_trace(ch)
        param = tr_state.parameter.upper()
        fmt = tr_state.format
        self._backend_set_measurement(ch, param)
        self._backend_write(self._xlat.set_trace_format(ch, fmt))
        self._backend_trigger(ch)
        return self._backend_query(self._xlat.query_selected_fdata(ch))

    def _handle_data_raw(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        param = cmd.arguments.strip().strip('"').upper()
        self._backend_set_measurement(ch, param)
        self._backend_trigger(ch)
        return self._backend_query(self._xlat.query_raw_data(ch, param))

    def _handle_data_corr(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        param = cmd.arguments.strip().strip('"').upper()
        self._backend_set_measurement(ch, param)
        self._backend_trigger(ch)
        return self._backend_query(self._xlat.query_sdata(ch, param))

    # -- Helper --

    def _find_active_trace(self, ch: int):
        """Find the active trace for a channel."""
        from vnasim.models.common import TraceState
        for t in self._traces.values():
            if t.channel == ch:
                return t
        return TraceState(channel=ch)
