"""Tests for the E5071B ENA model."""

import pytest

from vnasim.models.keysight_ena import E5071BModel
from vnasim.scpi.types import Unhandled


class TestE5071BModel:
    @pytest.fixture
    def model(self):
        return E5071BModel(
            num_ports=2,
            idn="Agilent Technologies,E5071B,MY00000001,A.09.00",
        )

    # -- identity / basics --

    def test_idn(self, model):
        assert model.handle("*IDN?") == "Agilent Technologies,E5071B,MY00000001,A.09.00"

    def test_opc(self, model):
        assert model.handle("*OPC?") == "1"

    def test_rst(self, model):
        model.handle(":SENS1:FREQ:STAR 500e6")
        model.handle("*RST")
        assert model.handle(":SENS1:FREQ:STAR?") == str(100e6)

    # -- ENA-style abbreviated commands --

    def test_freq_start_abbreviated(self, model):
        model.handle(":SENS1:FREQ:STAR 1e6")
        assert model.handle(":SENS1:FREQ:STAR?") == "1000000.0"

    def test_freq_stop_abbreviated(self, model):
        model.handle(":SENS1:FREQ:STOP 8.5e9")
        assert model.handle(":SENS1:FREQ:STOP?") == "8500000000.0"

    def test_sweep_points_abbreviated(self, model):
        model.handle(":SENS1:SWE:POIN 401")
        assert model.handle(":SENS1:SWE:POIN?") == "401"

    def test_sweep_type_abbreviated(self, model):
        model.handle(":SENS1:SWE:TYPE LIN")
        assert model.handle(":SENS1:SWE:TYPE?") == "LIN"

    def test_sweep_time_query(self, model):
        assert model.handle(":SENS1:SWE:TIME?") is not None

    # -- ENA-specific IFBW (no :RES suffix) --

    def test_ifbw_direct(self, model):
        model.handle(":SENS1:BAND 3000")
        assert model.handle(":SENS1:BAND?") == "3000.0"

    def test_ifbw_with_res_also_works(self, model):
        """SNA5000-style :BAND:RES also works on the ENA model."""
        model.handle(":SENS1:BAND:RES 5000")
        assert model.handle(":SENS1:BAND:RES?") == "5000.0"

    # -- ENA-specific data paths --

    def test_calc_data_sdat(self, model):
        model.handle(":SENS1:SWE:POIN 5")
        model.handle(":CALC1:PAR1:DEF S21")
        model.handle(":CALC1:PAR1:SEL")
        raw = model.handle(":CALC1:DATA:SDAT?")
        vals = raw.split(",")
        assert len(vals) == 10  # 5 points * 2 (re, im)

    def test_calc_data_fdat(self, model):
        model.handle(":SENS1:SWE:POIN 5")
        model.handle(":CALC1:PAR1:DEF S11")
        model.handle(":CALC1:PAR1:SEL")
        model.handle(":CALC1:FORM MLOG")
        raw = model.handle(":CALC1:DATA:FDAT?")
        vals = raw.split(",")
        assert len(vals) == 10
        # MLOGarithmic: imaginary values should be "0"
        for i in range(1, len(vals), 2):
            assert vals[i] == "0"

    # -- ENA-specific trace format --

    def test_calc_form_set(self, model):
        """`:CALC1:FORM MLOG` sets trace format."""
        model.handle(":CALC1:PAR1:DEF S11")
        model.handle(":CALC1:PAR1:SEL")
        model.handle(":CALC1:FORM MLOG")
        # Verify format was applied by reading FDAT

    # -- parameter count --

    def test_par_count_query(self, model):
        assert model.handle(":CALC1:PAR:COUN?") == "1"

    def test_par_count_set_accepted(self, model):
        assert model.handle(":CALC1:PAR:COUN 1") is None  # no-op

    # -- data format --

    def test_form_data_set(self, model):
        assert model.handle(":FORM:DATA ASC") is None  # no-op

    def test_form_data_query(self, model):
        assert model.handle(":FORM:DATA?") == "ASC"

    # -- service port count --

    def test_serv_port_count_2port(self, model):
        assert model.handle(":SERV:PORT:COUN?") == "2"

    def test_serv_port_count_4port(self):
        model = E5071BModel(num_ports=4)
        assert model.handle(":SERV:PORT:COUN?") == "4"

    # -- channel activation --

    def test_disp_wind_activate(self, model):
        model.handle(":DISP:WIND1:ACT")
        # Should not error

    # -- trigger (ENA-style, no :SEQ:) --

    def test_trig_sour_bus(self, model):
        model.handle(":TRIG:SOUR BUS")
        # Should not error

    def test_trig_sing(self, model):
        model.handle(":TRIG:SING")
        # Should not error

    def test_init_cont(self, model):
        model.handle(":INIT1:CONT ON")
        # Should not error

    # -- ENA trigger still works with SNA5000 paths --

    def test_trig_seq_sour_also_works(self, model):
        model.handle(":TRIG:SEQ:SOUR BUS")

    def test_trig_seq_sing_also_works(self, model):
        model.handle(":TRIG:SEQ:SING")

    # -- full ENA measurement sequence --

    def test_full_ena_sweep(self, model):
        """Simulate the exact command sequence KeysightENADriver sends."""
        # post_connect
        model.handle(":FORM:DATA ASC")
        assert model.handle(":SERV:PORT:COUN?") == "2"

        # get_frequency
        model.handle(":SENS1:FREQ:STAR 300000.0")
        model.handle(":SENS1:FREQ:STOP 8500000000.0")
        assert model.handle("*OPC?") == "1"
        assert model.handle(":SENS1:FREQ:STAR?") == "300000.0"
        assert model.handle(":SENS1:FREQ:STOP?") == "8500000000.0"

        # set_num_points
        model.handle(":SENS1:SWE:POIN 201")
        assert model.handle("*OPC?") == "1"
        assert model.handle(":SENS1:SWE:POIN?") == "201"

        # set_if_bandwidth
        model.handle(":SENS1:BAND 1000")
        assert model.handle("*OPC?") == "1"

        # _setup_trace + trigger + read SDAT (get_s_parameter)
        model.handle(":CALC1:PAR:COUN 1")
        model.handle(":CALC1:PAR1:DEF S11")
        model.handle(":CALC1:PAR1:SEL")
        model.handle(":DISP:WIND1:ACT")
        model.handle(":INIT1:CONT ON")
        model.handle(":TRIG:SOUR BUS")
        assert model.handle(":SENS1:SWE:TIME?") is not None
        model.handle(":TRIG:SING")
        assert model.handle("*OPC?") == "1"
        model.handle(":TRIG:SOUR INT")

        raw = model.handle(":CALC1:DATA:SDAT?")
        vals = raw.split(",")
        assert len(vals) == 402  # 201 points * 2

        # frequency list
        freq_raw = model.handle(":SENS1:FREQ:DATA?")
        freqs = freq_raw.split(",")
        assert len(freqs) == 201

    # -- correction --

    def test_corr_state(self, model):
        assert model.handle(":SENS1:CORR:STAT?") == "OFF"
        model.handle(":SENS1:CORR:STAT ON")
        assert model.handle(":SENS1:CORR:STAT?") == "ON"

    def test_corr_coef_query_abbreviated(self, model):
        """ENA queries coefficients at :SENS1:CORR:COEF? (no :DATA)."""
        model.handle(":SENS1:SWE:POIN 3")
        raw = model.handle(":SENS1:CORR:COEF? ED,1,1")
        vals = [float(x) for x in raw.split(",")]
        assert len(vals) == 6  # 3 points * 2 (re, im)

    # -- averaging / smoothing (abbreviated) --

    def test_averaging_abbreviated(self, model):
        assert model.handle(":SENS1:AVER?") == "OFF"
        model.handle(":SENS1:AVER OFF")

    def test_smoothing_abbreviated(self, model):
        assert model.handle(":CALC1:SMO?") == "OFF"

    # -- power (abbreviated) --

    def test_power_abbreviated(self, model):
        model.handle(":SOUR1:POW -10.0")
        assert model.handle(":SOUR1:POW?") == "-10.0"

    # -- display scale (abbreviated) --

    def test_display_scale_abbreviated(self, model):
        model.handle(":DISP:WIND1:TRAC1:Y:RLEV -20.0")
        assert model.handle(":DISP:WIND1:TRAC1:Y:RLEV?") == "-20.0"
        model.handle(":DISP:WIND1:TRAC1:Y:PDIV 5.0")
        assert model.handle(":DISP:WIND1:TRAC1:Y:PDIV?") == "5.0"
        model.handle(":DISP:WIND1:TRAC1:Y:RPOS 8")
        assert model.handle(":DISP:WIND1:TRAC1:Y:RPOS?") == "8"

    # -- segment data --

    def test_segment_data(self, model):
        seg = "5,0,1,1,0,0,1,1e6,6e9,201,1000,0"
        model.handle(f":SENS1:SEGM:DATA {seg}")
        assert model.handle(":SENS1:SEGM:DATA?") == seg
