"""Tests for Copper Mountain, R&S ZNB, and Anritsu ShockLine models."""

import pytest

from vnasim.models.copper_mountain import CopperMountainModel
from vnasim.models.rs_znb import RSZNBModel
from vnasim.models.anritsu_shockline import AnritsuShockLineModel


# =====================================================================
# Copper Mountain
# =====================================================================

class TestCopperMountain:
    @pytest.fixture
    def model(self):
        return CopperMountainModel(num_ports=2, idn="CMT,S2VNA,SN00001,1.0.0/1.0")

    def test_idn(self, model):
        assert "CMT" in model.handle("*IDN?")

    def test_ifbw_bwid(self, model):
        """CMT uses :BWID not :BAND."""
        model.handle(":SENS1:BWID 3000")
        assert model.handle(":SENS1:BWID?") == "3000.0"

    def test_ifbw_band_also_works(self, model):
        """E5071B-style :BAND still works (inherited)."""
        model.handle(":SENS1:BAND 5000")
        assert model.handle(":SENS1:BAND?") == "5000.0"

    def test_freq_xax(self, model):
        """CMT uses :CALC:DATA:XAX? for frequency list."""
        model.handle(":SENS1:SWE:POIN 5")
        raw = model.handle(":CALC1:DATA:XAX?")
        assert len(raw.split(",")) == 5

    def test_smoothing_trac(self, model):
        """CMT uses :CALC:TRAC:SMOO."""
        assert model.handle(":CALC1:TRAC:SMOO?") == "OFF"
        model.handle(":CALC1:TRAC:SMOO ON")
        assert model.handle(":CALC1:TRAC:SMOO?") == "ON"

    def test_smoothing_trac_aper(self, model):
        model.handle(":CALC1:TRAC:SMOO:APER 7.5")
        assert model.handle(":CALC1:TRAC:SMOO:APER?") == "7.5"

    def test_cw_freq(self, model):
        model.handle(":SENS1:FREQ:CW 1.5e9")
        assert model.handle(":SENS1:FREQ:CW?") == "1500000000.0"

    def test_full_sweep(self, model):
        model.handle(":FORM:DATA ASC")
        assert model.handle(":SERV:PORT:COUN?") == "2"
        model.handle(":SENS1:FREQ:STAR 1e6")
        model.handle(":SENS1:FREQ:STOP 6e9")
        model.handle(":SENS1:SWE:POIN 11")
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
        assert len(raw.split(",")) == 22
        xax = model.handle(":CALC1:DATA:XAX?")
        assert len(xax.split(",")) == 11


# =====================================================================
# R&S ZNB
# =====================================================================

class TestRSZNB:
    @pytest.fixture
    def model(self):
        return RSZNBModel(
            num_ports=4,
            idn="Rohde&Schwarz,ZNB8-4Port,1234567890,3.40",
        )

    def test_idn(self, model):
        assert "ZNB8" in model.handle("*IDN?")

    def test_port_count(self, model):
        assert model.handle(":INST:NPORT:COUN?") == "4"

    def test_par_sdef(self, model):
        """Named trace definition."""
        model.handle(":CALC1:PAR:SDEF 'VNALab','S21'")
        # Trace 1 should now be S21
        cat = model.handle(":CALC1:PAR:CAT?")
        assert "S21" in cat

    def test_par_sel_named(self, model):
        model.handle(":CALC1:PAR:SEL 'VNALab'")

    def test_par_del(self, model):
        model.handle(":CALC1:PAR:DEL 'VNALab'")

    def test_data_query_sdat(self, model):
        """``CALC:DATA? SDAT`` — argument after ?."""
        model.handle(":SENS1:SWE:POIN 5")
        model.handle(":CALC1:PAR:SDEF 'VNALab','S11'")
        model.handle(":CALC1:PAR:SEL 'VNALab'")
        raw = model.handle(":CALC1:DATA? SDAT")
        assert len(raw.split(",")) == 10

    def test_data_query_fdat(self, model):
        model.handle(":SENS1:SWE:POIN 5")
        model.handle(":CALC1:PAR:SDEF 'VNALab','S11'")
        model.handle(":CALC1:PAR:SEL 'VNALab'")
        model.handle(":CALC1:FORM MLOG")
        raw = model.handle(":CALC1:DATA? FDAT")
        assert len(raw.split(",")) == 10

    def test_data_stim(self, model):
        model.handle(":SENS1:SWE:POIN 5")
        raw = model.handle(":CALC1:DATA:STIM?")
        assert len(raw.split(",")) == 5

    def test_data_call(self, model):
        model.handle(":SENS1:SWE:POIN 5")
        model.handle(":CALC1:PAR:SDEF 'VNALab','S11'")
        raw = model.handle(":CALC1:DATA:CALL? SDAT")
        assert len(raw.split(",")) == 10

    def test_disp_wind_stat(self, model):
        model.handle(":DISP:WIND1:STAT ON")
        assert model.handle(":DISP:WIND1:STAT?") == "ON"

    def test_disp_trac_feed(self, model):
        model.handle(":DISP:WIND1:TRAC1:FEED 'VNALab'")

    def test_trigger_init_imm(self, model):
        """R&S uses INIT:CONT OFF + INIT:IMM (inherited from E5071B chain)."""
        model.handle(":INIT1:CONT OFF")
        model.handle(":INIT1:IMM")
        assert model.handle("*OPC?") == "1"

    def test_corr_cdat(self, model):
        """R&S cal coefficients via CORR:CDAT."""
        model.handle(":SENS1:SWE:POIN 3")
        raw = model.handle(":SENS1:CORR:CDAT? 'DIRECTIVITY',1,0")
        vals = [float(x) for x in raw.split(",")]
        assert len(vals) == 6

    def test_corr_coll_meth(self, model):
        model.handle(":SENS1:CORR:COLL:METH:DEF 'VNALab_Cal',TOSM,1,2")

    def test_corr_coll_save(self, model):
        model.handle(":SENS1:CORR:COLL:SAVE:SEL:DEF")

    def test_full_sweep(self, model):
        model.handle(":FORM:DATA ASC")
        assert model.handle(":INST:NPORT:COUN?") == "4"
        model.handle(":SENS1:FREQ:STAR 9000")
        model.handle(":SENS1:FREQ:STOP 8.5e9")
        model.handle(":SENS1:SWE:POIN 11")
        model.handle(":CALC1:PAR:SDEF 'VNALab','S11'")
        model.handle(":DISP:WIND1:STAT ON")
        model.handle(":DISP:WIND1:TRAC1:FEED 'VNALab'")
        model.handle(":CALC1:PAR:SEL 'VNALab'")
        model.handle(":INIT1:CONT OFF")
        model.handle(":INIT1:IMM")
        assert model.handle("*OPC?") == "1"
        raw = model.handle(":CALC1:DATA? SDAT")
        assert len(raw.split(",")) == 22
        stim = model.handle(":CALC1:DATA:STIM?")
        assert len(stim.split(",")) == 11


# =====================================================================
# Anritsu ShockLine
# =====================================================================

class TestAnritsuShockLine:
    @pytest.fixture
    def model(self):
        return AnritsuShockLineModel(
            num_ports=2,
            idn="Anritsu,MS46522B,1234567890,1.0.0",
        )

    def test_idn(self, model):
        assert "Anritsu" in model.handle("*IDN?")

    def test_sweep_type_typ(self, model):
        """Anritsu uses :SWE:TYP (3-char short form)."""
        model.handle(":SENS1:SWE:TYP LIN")
        assert model.handle(":SENS1:SWE:TYP?") == "LIN"
        model.handle(":SENS1:SWE:TYP FSEGM")
        assert model.handle(":SENS1:SWE:TYP?") == "FSEGM"

    def test_hold_func(self, model):
        model.handle(":SENS1:HOLD:FUNC HOLD")
        model.handle(":SENS1:HOLD:FUNC CONT")

    def test_freq_data(self, model):
        """Anritsu uses :SENS:FREQ:DATA? (like SNA5000)."""
        model.handle(":SENS1:SWE:POIN 5")
        raw = model.handle(":SENS1:FREQ:DATA?")
        assert len(raw.split(",")) == 5

    def test_corr_coef_anritsu_style(self, model):
        """Anritsu cal coefficients: single term name, no port args."""
        model.handle(":SENS1:SWE:POIN 3")
        raw = model.handle(":SENS1:CORR:COEF? ED1")
        vals = [float(x) for x in raw.split(",")]
        assert len(vals) == 6

    def test_corr_coef_write_anritsu(self, model):
        model.handle(":SENS1:SWE:POIN 2")
        model.handle(":SENS1:CORR:COEF ED1,0.01,0.02,0.03,0.04")
        raw = model.handle(":SENS1:CORR:COEF? ED1")
        vals = [float(x) for x in raw.split(",")]
        assert vals == pytest.approx([0.01, 0.02, 0.03, 0.04])

    def test_corr_coll_type(self, model):
        assert model.handle(":SENS1:CORR:COLL:TYP?") == "NONE"

    def test_corr_port_methods(self, model):
        """All port-specific cal method commands accepted."""
        model.handle(":SENS1:CORR:COEF:PORT12:FULL2")
        model.handle(":SENS1:CORR:COEF:PORT1:FULL1")
        model.handle(":SENS1:CORR:COEF:PORT2:RESP1")
        model.handle(":SENS1:CORR:COEF:PORT12:1P2PF")
        model.handle(":SENS1:CORR:COEF:PORT12:TFRF")

    def test_trigger_flow(self, model):
        """Anritsu trigger: HOLD:FUNC HOLD + TRIG:SING + OPC."""
        model.handle(":SENS1:HOLD:FUNC HOLD")
        model.handle(":TRIG:SING")
        assert model.handle("*OPC?") == "1"

    def test_full_sweep(self, model):
        model.handle(":FORM:DATA ASC")
        model.handle(":SENS1:FREQ:STAR 1e6")
        model.handle(":SENS1:FREQ:STOP 6e9")
        model.handle(":SENS1:SWE:POIN 11")
        model.handle(":CALC1:PAR:COUN 1")
        model.handle(":CALC1:PAR1:DEF S11")
        model.handle(":CALC1:PAR1:SEL")
        model.handle(":SENS1:HOLD:FUNC HOLD")
        model.handle(":TRIG:SING")
        assert model.handle("*OPC?") == "1"
        raw = model.handle(":CALC1:DATA:SDAT?")
        assert len(raw.split(",")) == 22
        freqs = model.handle(":SENS1:FREQ:DATA?")
        assert len(freqs.split(",")) == 11
