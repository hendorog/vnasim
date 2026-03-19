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

    def _backend_ch(self, frontend_ch: int) -> int | None:
        """Map frontend channel to backend channel, or None if local-only."""
        return 1 if frontend_ch in self._BACKEND_CHANNELS else None

    def _backend_query(self, scpi: str) -> str:
        return self._backend.query(scpi)

    def _backend_write(self, scpi: str) -> None:
        self._backend.write(scpi)

    def _backend_trigger(self, ch: int) -> None:
        """Trigger a sweep on the backend and wait for completion."""
        bch = self._backend_ch(ch)
        for cmd in self._xlat.trigger_sweep(bch):
            self._backend_write(cmd)
        self._backend_query("*OPC?")

    def _backend_set_measurement(self, ch: int, param: str) -> None:
        """Configure a measurement on the backend."""
        bch = self._backend_ch(ch)
        for cmd in self._xlat.set_measurement(bch, 1, param):
            self._backend_write(cmd)

    def _find_active_trace(self, ch: int) -> TraceState:
        for t in self._traces.values():
            if t.channel == ch:
                return t
        return TraceState(channel=ch)

    # ------------------------------------------------------------------
    # Overridden handlers — forwarded to backend
    # ------------------------------------------------------------------

    # -- Frequency --

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

    def _handle_freq_cw(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_freq_cw(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_freq_cw(bch))
        self._backend_write(self._xlat.set_freq_cw(bch, float(cmd.arguments)))
        return None

    def _handle_freq_data(self, cmd: ParsedCommand) -> str:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_freq_data(cmd)
        return self._backend_query(self._xlat.query_freq_data(bch))

    # -- Sweep --

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

    def _handle_swp_type(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_swp_type(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_swp_type(bch))
        self._backend_write(self._xlat.set_swp_type(bch, cmd.arguments.strip()))
        return None

    def _handle_swp_time(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_swp_time(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_swp_time(bch))
        return None

    # -- IFBW --

    def _handle_ifbw(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_ifbw(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_ifbw(bch))
        self._backend_write(self._xlat.set_ifbw(bch, float(cmd.arguments)))
        return None

    # -- Power --

    def _handle_src_power(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_src_power(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_power(bch))
        self._backend_write(self._xlat.set_power(bch, float(cmd.arguments)))
        return None

    # -- Averaging --

    def _handle_avg_state(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_avg_state(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_avg_state(bch))
        self._backend_write(self._xlat.set_avg_state(bch, cmd.arguments.strip()))
        return None

    def _handle_avg_count(self, cmd: ParsedCommand) -> str:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_avg_count(cmd)
        return self._backend_query(self._xlat.query_avg_count(bch))

    # -- Smoothing --

    def _handle_smooth_state(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_smooth_state(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_smooth_state(bch))
        self._backend_write(self._xlat.set_smooth_state(bch, cmd.arguments.strip()))
        return None

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

    def _handle_corr_state(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_corr_state(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_corr_state(bch))
        self._backend_write(self._xlat.set_corr_state(bch, cmd.arguments.strip()))
        return None

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

    def _handle_seg_data(self, cmd: ParsedCommand) -> str | None:
        bch = self._backend_ch(cmd.channel)
        if bch is None:
            return super()._handle_seg_data(cmd)
        if cmd.is_query:
            return self._backend_query(self._xlat.query_seg_data(bch))
        self._backend_write(self._xlat.set_seg_data(bch, cmd.arguments.strip()))
        return None

    # -- Data reads (the core value of the proxy) --

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

    def _handle_data_raw(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        bch = self._backend_ch(ch)
        if bch is None:
            return super()._handle_data_raw(cmd)
        param = cmd.arguments.strip().strip('"').upper()
        self._backend_set_measurement(ch, param)
        self._backend_trigger(ch)
        return self._backend_query(self._xlat.query_raw_data(bch, param))

    def _handle_data_corr(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        bch = self._backend_ch(ch)
        if bch is None:
            return super()._handle_data_corr(cmd)
        param = cmd.arguments.strip().strip('"').upper()
        self._backend_set_measurement(ch, param)
        self._backend_trigger(ch)
        return self._backend_query(self._xlat.query_sdata(bch, param))
