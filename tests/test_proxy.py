"""Tests for the proxy/emulator mode.

Spins up a synthetic SNA5000 as the backend, then connects a proxy
E5071B model to it and verifies cross-dialect data flow.
"""

import asyncio
import socket
import threading

import pytest

from vnasim.backend.client import BackendClient
from vnasim.backend.translator import SNA5000Translator
from vnasim.models.proxy import ProxyVNAModel
from vnasim.models.mixins import ENACommandsMixin, RSZNBCommandsMixin
from vnasim.models.sna5000 import SNA5000Model
from vnasim.server import start_instrument


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def backend_server():
    """Start a synthetic SNA5000 on an ephemeral port as the backend."""
    model = SNA5000Model(
        num_ports=2,
        idn="Siglent Technologies,SNA5012A,SNA5XXXX00001,2.3.1.3.1r1",
    )
    port = _find_free_port()
    ready = threading.Event()
    server_ref = []

    def run():
        async def start():
            srv = await start_instrument(model, port=port, name="backend",
                                         host="127.0.0.1")
            server_ref.append(srv)
            ready.set()
            await asyncio.Event().wait()
        asyncio.run(start())

    t = threading.Thread(target=run, daemon=True)
    t.start()
    ready.wait(timeout=5)
    yield port
    # cleanup happens when thread is killed (daemon)


class ProxyE5071B(ProxyVNAModel, ENACommandsMixin):
    def _build_tree(self):
        self._register_core()
        self._register_ena()


class ProxyRSZNB(ProxyVNAModel, ENACommandsMixin, RSZNBCommandsMixin):
    def _build_tree(self):
        self._register_core()
        self._register_ena()
        self._register_rs()


class TestProxyE5071B:
    """E5071B frontend dialect, SNA5000 backend."""

    @pytest.fixture
    def model(self, backend_server):
        backend = BackendClient("127.0.0.1", backend_server)
        backend.connect()
        proxy = ProxyE5071B(
            num_ports=2,
            idn="Agilent Technologies,E5071B,PROXY00001,A.09.00",
            backend=backend,
            translator=SNA5000Translator(),
        )
        yield proxy
        backend.disconnect()

    def test_idn_returns_frontend_identity(self, model):
        """IDN should return the emulated identity, not the backend's."""
        assert "E5071B" in model.handle("*IDN?")
        assert "SNA5" not in model.handle("*IDN?")

    def test_opc(self, model):
        assert model.handle("*OPC?") == "1"

    def test_freq_start_forwarded(self, model):
        """Setting frequency on the proxy forwards to the backend."""
        model.handle(":SENS1:FREQ:STAR 1e6")
        resp = model.handle(":SENS1:FREQ:STAR?")
        assert resp == "1000000.0"

    def test_freq_stop_forwarded(self, model):
        model.handle(":SENS1:FREQ:STOP 8.5e9")
        assert model.handle(":SENS1:FREQ:STOP?") == "8500000000.0"

    def test_sweep_points_forwarded(self, model):
        model.handle(":SENS1:SWE:POIN 201")
        assert model.handle(":SENS1:SWE:POIN?") == "201"

    def test_ifbw_forwarded(self, model):
        """E5071B sends :BAND, proxy translates to :BAND:RES for SNA5000."""
        model.handle(":SENS1:BAND 3000")
        assert model.handle(":SENS1:BAND?") == "3000.0"

    def test_power_forwarded(self, model):
        model.handle(":SOUR1:POW -10")
        assert model.handle(":SOUR1:POW?") == "-10.0"

    def test_sweep_time_from_backend(self, model):
        resp = model.handle(":SENS1:SWE:TIME?")
        assert float(resp) >= 0

    def test_sdata_returns_real_data(self, model):
        """Core test: SDAT query gets real data through the proxy."""
        model.handle(":SENS1:SWE:POIN 11")
        model.handle(":CALC1:PAR1:DEF S21")
        model.handle(":CALC1:PAR1:SEL")
        raw = model.handle(":CALC1:DATA:SDAT?")
        vals = raw.split(",")
        assert len(vals) == 22  # 11 points * 2 (re, im)
        # Values should be non-trivial (real data, not zeros)
        floats = [float(v) for v in vals]
        assert any(abs(f) > 1e-10 for f in floats)

    def test_freq_data_from_backend(self, model):
        model.handle(":SENS1:FREQ:STAR 1e6")
        model.handle(":SENS1:FREQ:STOP 6e9")
        model.handle(":SENS1:SWE:POIN 5")
        raw = model.handle(":SENS1:FREQ:DATA?")
        freqs = [float(f) for f in raw.split(",")]
        assert len(freqs) == 5
        assert freqs[0] == pytest.approx(1e6)
        assert freqs[-1] == pytest.approx(6e9)

    def test_correction_state_forwarded(self, model):
        model.handle(":SENS1:CORR:STAT ON")
        assert model.handle(":SENS1:CORR:STAT?") == "ON"
        model.handle(":SENS1:CORR:STAT OFF")
        assert model.handle(":SENS1:CORR:STAT?") == "OFF"

    def test_full_ena_measurement_sequence(self, model):
        """Simulate the exact command sequence KeysightENADriver sends."""
        model.handle(":FORM:DATA ASC")
        assert model.handle(":SERV:PORT:COUN?") == "2"

        model.handle(":SENS1:FREQ:STAR 300000")
        model.handle(":SENS1:FREQ:STOP 8.5e9")
        assert model.handle("*OPC?") == "1"

        model.handle(":SENS1:SWE:POIN 11")
        assert model.handle("*OPC?") == "1"

        model.handle(":SENS1:BAND 1000")
        assert model.handle("*OPC?") == "1"

        # Setup trace + read data (E5071B path)
        model.handle(":CALC1:PAR:COUN 1")
        model.handle(":CALC1:PAR1:DEF S11")
        model.handle(":CALC1:PAR1:SEL")
        model.handle(":DISP:WIND1:ACT")
        model.handle(":INIT1:CONT ON")
        model.handle(":TRIG:SOUR BUS")
        model.handle(":TRIG:SING")
        assert model.handle("*OPC?") == "1"
        model.handle(":TRIG:SOUR INT")

        raw = model.handle(":CALC1:DATA:SDAT?")
        vals = raw.split(",")
        assert len(vals) == 22  # 11 pts * 2

        freq_raw = model.handle(":SENS1:FREQ:DATA?")
        freqs = freq_raw.split(",")
        assert len(freqs) == 11


class TestProxyRSZNB:
    """R&S ZNB frontend dialect, SNA5000 backend."""

    @pytest.fixture
    def model(self, backend_server):
        backend = BackendClient("127.0.0.1", backend_server)
        backend.connect()
        proxy = ProxyRSZNB(
            num_ports=2,
            idn="Rohde&Schwarz,ZNB8-2Port,PROXY00001,3.40",
            backend=backend,
            translator=SNA5000Translator(),
        )
        yield proxy
        backend.disconnect()

    def test_idn(self, model):
        assert "ZNB8" in model.handle("*IDN?")

    def test_named_trace_then_data(self, model):
        """R&S named trace + DATA? SDAT through SNA5000 backend."""
        model.handle(":SENS1:SWE:POIN 5")
        model.handle(":CALC1:PAR:SDEF 'VNALab','S11'")
        model.handle(":CALC1:PAR:SEL 'VNALab'")
        raw = model.handle(":CALC1:DATA? SDAT")
        vals = raw.split(",")
        assert len(vals) == 10

    def test_stim_data(self, model):
        model.handle(":SENS1:SWE:POIN 5")
        raw = model.handle(":CALC1:DATA:STIM?")
        assert len(raw.split(",")) == 5
