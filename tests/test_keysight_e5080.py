"""Tests for the E5080A/B model."""

import pytest

from vnasim.models.keysight_e5080 import E5080Model


class TestE5080Model:
    @pytest.fixture
    def model(self):
        return E5080Model(
            num_ports=2,
            idn="Keysight Technologies,E5080B,US00000001,A.15.00.00",
        )

    # -- identity --

    def test_idn(self, model):
        assert "E5080B" in model.handle("*IDN?")

    def test_opc(self, model):
        assert model.handle("*OPC?") == "1"

    # -- port detection --

    def test_syst_port_count(self, model):
        assert model.handle(":SYST:CAP:HARD:PORT:INT:COUN?") == "2"

    def test_syst_port_count_4port(self):
        m = E5080Model(num_ports=4)
        assert m.handle(":SYST:CAP:HARD:PORT:INT:COUN?") == "4"

    # -- channel catalog --

    def test_chan_catalog(self, model):
        raw = model.handle(":SYST:CHAN:CAT?")
        assert raw.startswith('"')
        assert "1" in raw

    # -- data format --

    def test_form_data(self, model):
        model.handle(":FORM:DATA ASC")
        assert model.handle(":FORM:DATA?") == "ASC"

    # -- frequency / sweep --

    def test_freq(self, model):
        model.handle(":SENS1:FREQ:STAR 300000")
        model.handle(":SENS1:FREQ:STOP 8.5e9")
        assert model.handle(":SENS1:FREQ:STAR?") == "300000.0"
        assert model.handle(":SENS1:FREQ:STOP?") == "8500000000.0"

    def test_sweep_points(self, model):
        model.handle(":SENS1:SWE:POIN 201")
        assert model.handle(":SENS1:SWE:POIN?") == "201"

    def test_ifbw(self, model):
        model.handle(":SENS1:BAND 3000")
        assert model.handle(":SENS1:BAND?") == "3000.0"

    def test_sweep_type(self, model):
        model.handle(":SENS1:SWE:TYPE LIN")
        resp = model.handle(":SENS1:SWE:TYPE?")
        assert resp is not None

    def test_cw_freq(self, model):
        model.handle(":SENS1:FREQ:CW 2.5e9")
        assert model.handle(":SENS1:FREQ:CW?") == "2500000000.0"

    # -- sweep mode & initiate --

    def test_swp_mode(self, model):
        model.handle(":SENS1:SWE:MODE SING")

    def test_init_imm(self, model):
        model.handle(":INIT1:IMM")

    # -- measurement model --

    def test_meas_def(self, model):
        model.handle(':CALC1:MEAS1:DEF "S21"')
        assert model.handle(":CALC1:MEAS1:DEF?") == "S21"

    def test_meas_par(self, model):
        model.handle(':CALC1:MEAS1:DEF "S11"')
        assert model.handle(":CALC1:MEAS1:PAR?") == "S11"

    def test_meas_sdata(self, model):
        model.handle(":SENS1:SWE:POIN 5")
        model.handle(':CALC1:MEAS1:DEF "S21"')
        raw = model.handle(":CALC1:MEAS1:DATA:SDATA?")
        vals = raw.split(",")
        assert len(vals) == 10

    def test_meas_fdata(self, model):
        model.handle(":SENS1:SWE:POIN 5")
        model.handle(':CALC1:MEAS1:DEF "S11"')
        model.handle(":CALC1:MEAS1:FORM MLOG")
        raw = model.handle(":CALC1:MEAS1:DATA:FDATA?")
        vals = raw.split(",")
        assert len(vals) == 10
        for i in range(1, len(vals), 2):
            assert vals[i] == "0"

    def test_meas_x(self, model):
        model.handle(":SENS1:SWE:POIN 11")
        model.handle(':CALC1:MEAS1:DEF "S11"')
        raw = model.handle(":CALC1:MEAS1:X?")
        vals = raw.split(",")
        assert len(vals) == 11

    def test_meas_form(self, model):
        model.handle(':CALC1:MEAS1:DEF "S11"')
        model.handle(":CALC1:MEAS1:FORM PHAS")
        assert model.handle(":CALC1:MEAS1:FORM?") == "PHAS"

    # -- display --

    def test_disp_wind_state(self, model):
        model.handle(":DISP:WIND1:STATE ON")

    def test_disp_meas_feed(self, model):
        model.handle(":DISP:MEAS1:FEED 1")

    def test_disp_meas_scale(self, model):
        model.handle(":DISP:MEAS1:Y:RLEV -20.0")
        assert model.handle(":DISP:MEAS1:Y:RLEV?") == "-20.0"
        model.handle(":DISP:MEAS1:Y:PDIV 5.0")
        assert model.handle(":DISP:MEAS1:Y:PDIV?") == "5.0"
        model.handle(":DISP:MEAS1:Y:RPOS 8")
        assert model.handle(":DISP:MEAS1:Y:RPOS?") == "8"

    # -- averaging / smoothing --

    def test_averaging(self, model):
        assert model.handle(":SENS1:AVER?") == "OFF"
        model.handle(":SENS1:AVER OFF")

    def test_smoothing_per_meas(self, model):
        assert model.handle(":CALC1:MEAS1:SMO?") == "OFF"
        model.handle(":CALC1:MEAS1:SMO ON")
        assert model.handle(":CALC1:MEAS1:SMO?") == "ON"

    # -- power --

    def test_power(self, model):
        model.handle(":SOUR1:POW -10")
        assert model.handle(":SOUR1:POW?") == "-10.0"

    # -- correction --

    def test_corr_state(self, model):
        assert model.handle(":SENS1:CORR:STAT?") == "OFF"
        model.handle(":SENS1:CORR:STAT ON")
        assert model.handle(":SENS1:CORR:STAT?") == "ON"

    # -- cal set --

    def test_cset_create(self, model):
        model.handle(":SENS1:CORR:CSET:CRE 'test_cal'")

    def test_cset_data_query(self, model):
        model.handle(":SENS1:SWE:POIN 3")
        raw = model.handle(":SENS1:CORR:CSET:DATA? EDIR,1,1")
        vals = [float(x) for x in raw.split(",")]
        assert len(vals) == 6

    def test_cset_save(self, model):
        model.handle(":SENS1:CORR:CSET:SAVE")

    def test_cset_activate(self, model):
        model.handle(":SENS1:CORR:CSET:ACT 'test_cal',0")

    # -- segments --

    def test_segment_flow(self, model):
        model.handle(":SENS1:SEGM:DEL:ALL")
        assert model.handle(":SENS1:SEGM:COUN?") == "0"

        model.handle(":SENS1:SEGM1:ADD")
        assert model.handle(":SENS1:SEGM:COUN?") == "1"

        model.handle(":SENS1:SEGM1:FREQ:STAR 1e6")
        model.handle(":SENS1:SEGM1:FREQ:STOP 3e9")
        model.handle(":SENS1:SEGM1:SWE:POIN 101")
        model.handle(":SENS1:SEGM1:BWID 1000")
        assert model.handle(":SENS1:SEGM1:FREQ:STAR?") == "1000000.0"
        assert model.handle(":SENS1:SEGM1:SWE:POIN?") == "101"

        model.handle(":SENS1:SEGM2:ADD")
        model.handle(":SENS1:SEGM2:FREQ:STAR 4e9")
        model.handle(":SENS1:SEGM2:FREQ:STOP 8.5e9")
        model.handle(":SENS1:SEGM2:SWE:POIN 201")
        assert model.handle(":SENS1:SEGM:COUN?") == "2"
        assert model.handle(":SENS1:SEGM2:FREQ:STOP?") == "8500000000.0"

    def test_seg_bwid_cont(self, model):
        model.handle(":SENS1:SEGM:BWID:CONT ON")

    def test_seg_pow_cont(self, model):
        model.handle(":SENS1:SEGM:POW:CONT ON")

    # -- full E5080 measurement sequence --

    def test_full_e5080_sweep(self, model):
        """Simulate the exact command sequence KeysightE5080Driver sends."""
        # _post_connect
        model.handle(":FORM:DATA ASC")
        assert model.handle(":SYST:CAP:HARD:PORT:INT:COUN?") == "2"

        # configure
        model.handle(":SENS1:FREQ:STAR 300000")
        model.handle(":SENS1:FREQ:STOP 8.5e9")
        assert model.handle("*OPC?") == "1"
        model.handle(":SENS1:SWE:POIN 201")
        assert model.handle("*OPC?") == "1"
        model.handle(":SENS1:BAND 1000")
        assert model.handle("*OPC?") == "1"

        # _ensure_measurement + trigger + read
        model.handle(':CALC1:MEAS1:DEF "S11"')
        model.handle(":DISP:WIND1:STATE ON")
        model.handle(":DISP:MEAS1:FEED 1")
        model.handle(":SENS1:SWE:MODE SING")
        model.handle(":INIT1:IMM")
        assert model.handle("*OPC?") == "1"

        raw = model.handle(":CALC1:MEAS1:DATA:SDATA?")
        vals = raw.split(",")
        assert len(vals) == 402

        x_raw = model.handle(":CALC1:MEAS1:X?")
        x_vals = x_raw.split(",")
        assert len(x_vals) == 201
