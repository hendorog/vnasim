"""Tests for newly implemented E5071B features backed by SNA5000."""

import pytest
import numpy as np

from vnasim.models.keysight_ena import E5071BModel
from vnasim.models.sna5000 import SNA5000Model
from vnasim.scpi.types import Unhandled


class TestIEEE488:
    """IEEE 488.2 common commands."""

    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        return E5071BModel(num_ports=2)

    # Cyclomatic complexity: 1
    def test_cls(self, model):
        assert model.handle("*CLS") is None

    # Cyclomatic complexity: 1
    def test_ese_set_query(self, model):
        model.handle("*ESE 255")
        assert model.handle("*ESE?") == "255"

    # Cyclomatic complexity: 1
    def test_esr_query(self, model):
        assert model.handle("*ESR?") == "0"

    # Cyclomatic complexity: 1
    def test_sre_set_query(self, model):
        model.handle("*SRE 128")
        assert model.handle("*SRE?") == "128"

    # Cyclomatic complexity: 1
    def test_stb_query(self, model):
        assert model.handle("*STB?") == "0"

    # Cyclomatic complexity: 1
    def test_wai(self, model):
        assert model.handle("*WAI") is None

    # Cyclomatic complexity: 1
    def test_trg(self, model):
        assert model.handle("*TRG") is None


class TestSystemCommands:
    """System, abort, output."""

    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        return E5071BModel(num_ports=2)

    # Cyclomatic complexity: 1
    def test_sys_err(self, model):
        assert model.handle(":SYST:ERR?") == '0,"No error"'

    # Cyclomatic complexity: 1
    def test_sys_pres(self, model):
        model.handle(":SENS1:FREQ:STAR 500e6")
        model.handle(":SYST:PRES")
        assert model.handle(":SENS1:FREQ:STAR?") == str(100e6)

    # Cyclomatic complexity: 1
    def test_abort(self, model):
        assert model.handle(":ABOR") is None

    # Cyclomatic complexity: 1
    def test_output_state(self, model):
        assert model.handle(":OUTP?") == "1"
        model.handle(":OUTP OFF")
        assert model.handle(":OUTP?") == "0"
        model.handle(":OUTP ON")
        assert model.handle(":OUTP?") == "1"


class TestFreqCenterSpan:
    """Frequency center/span commands."""

    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        return E5071BModel(num_ports=2)

    # Cyclomatic complexity: 1
    def test_freq_center_query(self, model):
        model.handle(":SENS1:FREQ:STAR 1e9")
        model.handle(":SENS1:FREQ:STOP 3e9")
        assert model.handle(":SENS1:FREQ:CENT?") == "2000000000.0"

    # Cyclomatic complexity: 1
    def test_freq_span_query(self, model):
        model.handle(":SENS1:FREQ:STAR 1e9")
        model.handle(":SENS1:FREQ:STOP 3e9")
        assert model.handle(":SENS1:FREQ:SPAN?") == "2000000000.0"

    # Cyclomatic complexity: 1
    def test_freq_center_set(self, model):
        model.handle(":SENS1:FREQ:STAR 1e9")
        model.handle(":SENS1:FREQ:STOP 3e9")
        model.handle(":SENS1:FREQ:CENT 4e9")
        # Span should stay 2 GHz, so start=3G, stop=5G
        assert float(model.handle(":SENS1:FREQ:STAR?")) == pytest.approx(3e9)
        assert float(model.handle(":SENS1:FREQ:STOP?")) == pytest.approx(5e9)

    # Cyclomatic complexity: 1
    def test_freq_span_set(self, model):
        model.handle(":SENS1:FREQ:STAR 1e9")
        model.handle(":SENS1:FREQ:STOP 3e9")
        model.handle(":SENS1:FREQ:SPAN 4e9")
        # Center should stay 2 GHz, so start=0, stop=4G
        assert float(model.handle(":SENS1:FREQ:STAR?")) == pytest.approx(0.0)
        assert float(model.handle(":SENS1:FREQ:STOP?")) == pytest.approx(4e9)


class TestSweepDelay:
    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        return E5071BModel(num_ports=2)

    # Cyclomatic complexity: 1
    def test_sweep_delay_set_query(self, model):
        model.handle(":SENS1:SWE:DEL 0.001")
        assert model.handle(":SENS1:SWE:DEL?") == "0.001"


class TestAveragingEnhancements:
    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        return E5071BModel(num_ports=2)

    # Cyclomatic complexity: 1
    def test_avg_count_set_query(self, model):
        model.handle(":SENS1:AVER:COUN 16")
        assert model.handle(":SENS1:AVER:COUN?") == "16"

    # Cyclomatic complexity: 1
    def test_avg_clear(self, model):
        assert model.handle(":SENS1:AVER:CLE") is None


class TestElectricalDelay:
    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        return E5071BModel(num_ports=2)

    # Cyclomatic complexity: 1
    def test_elec_delay_set_query(self, model):
        model.handle(":CALC1:CORR:EDEL:TIME 1.5e-9")
        assert model.handle(":CALC1:CORR:EDEL:TIME?") == "1.5e-09"

    # Cyclomatic complexity: 1
    def test_phase_offset_set_query(self, model):
        model.handle(":CALC1:CORR:OFFS:PHAS 45.0")
        assert model.handle(":CALC1:CORR:OFFS:PHAS?") == "45.0"


class TestMarkers:
    """Marker commands — E5071B dialect."""

    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        m = E5071BModel(num_ports=2)
        m.handle(":SENS1:SWE:POIN 201")
        m.handle(":CALC1:PAR1:DEF S11")
        m.handle(":CALC1:PAR1:SEL")
        return m

    # Cyclomatic complexity: 1
    def test_marker_state(self, model):
        assert model.handle(":CALC1:MARK1:STAT?") == "0"
        model.handle(":CALC1:MARK1:STAT ON")
        assert model.handle(":CALC1:MARK1:STAT?") == "1"

    # Cyclomatic complexity: 1
    def test_marker_activate(self, model):
        model.handle(":CALC1:MARK3:ACT")
        assert model.handle(":CALC1:MARK3:STAT?") == "1"

    # Cyclomatic complexity: 1
    def test_marker_x_set_query(self, model):
        model.handle(":CALC1:MARK1:X 2e9")
        assert model.handle(":CALC1:MARK1:X?") == "2000000000.0"

    # Cyclomatic complexity: 1
    def test_marker_y_query(self, model):
        model.handle(":CALC1:FORM MLOG")
        model.handle(":CALC1:MARK1:STAT ON")
        model.handle(":CALC1:MARK1:X 1.5e9")
        result = model.handle(":CALC1:MARK1:Y?")
        vals = result.split(",")
        assert len(vals) == 2
        # MLOG format: dB value, 0
        assert vals[1] == "0"

    # Cyclomatic complexity: 1
    def test_marker_discrete(self, model):
        model.handle(":CALC1:MARK1:DISC ON")
        assert model.handle(":CALC1:MARK1:DISC?") == "1"

    # Cyclomatic complexity: 1
    def test_marker_coupling(self, model):
        model.handle(":CALC1:MARK:COUP ON")
        assert model.handle(":CALC1:MARK:COUP?") == "1"

    # Cyclomatic complexity: 1
    def test_marker_ref_state(self, model):
        model.handle(":CALC1:MARK:REF ON")
        assert model.handle(":CALC1:MARK:REF?") == "1"

    # Cyclomatic complexity: 1
    def test_marker_func_type(self, model):
        model.handle(":CALC1:MARK1:FUNC:TYPE MAXimum")
        assert model.handle(":CALC1:MARK1:FUNC:TYPE?") == "MAXimum"

    # Cyclomatic complexity: 1
    def test_marker_func_exec(self, model):
        model.handle(":CALC1:MARK1:STAT ON")
        model.handle(":CALC1:MARK1:FUNC:TYPE MAXimum")
        model.handle(":CALC1:MARK1:FUNC:EXEC")
        x = float(model.handle(":CALC1:MARK1:X?"))
        assert x >= 100e6  # within frequency range

    # Cyclomatic complexity: 1
    def test_marker_func_target(self, model):
        model.handle(":CALC1:MARK1:FUNC:TARG -20.0")
        assert model.handle(":CALC1:MARK1:FUNC:TARG?") == "-20.0"

    # Cyclomatic complexity: 1
    def test_marker_func_tracking(self, model):
        model.handle(":CALC1:MARK1:FUNC:TRAC ON")
        assert model.handle(":CALC1:MARK1:FUNC:TRAC?") == "1"

    # Cyclomatic complexity: 1
    def test_marker_func_domain(self, model):
        model.handle(":CALC1:MARK1:FUNC:DOM ON")
        assert model.handle(":CALC1:MARK1:FUNC:DOM?") == "1"
        model.handle(":CALC1:MARK1:FUNC:DOM:STAR 1e9")
        assert model.handle(":CALC1:MARK1:FUNC:DOM:STAR?") == "1000000000.0"
        model.handle(":CALC1:MARK1:FUNC:DOM:STOP 2e9")
        assert model.handle(":CALC1:MARK1:FUNC:DOM:STOP?") == "2000000000.0"

    # Cyclomatic complexity: 1
    def test_marker_bw_search(self, model):
        model.handle(":CALC1:MARK1:BWID ON")
        assert model.handle(":CALC1:MARK1:BWID?") == "1"
        model.handle(":CALC1:MARK1:BWID:THR -3.0")
        assert model.handle(":CALC1:MARK1:BWID:THR?") == "-3.0"
        result = model.handle(":CALC1:MARK1:BWID:DATA?")
        vals = result.split(",")
        assert len(vals) == 4  # bw, center, q, loss

    # Cyclomatic complexity: 1
    def test_marker_set_center(self, model):
        model.handle(":SENS1:FREQ:STAR 1e9")
        model.handle(":SENS1:FREQ:STOP 3e9")
        model.handle(":CALC1:MARK1:X 2.5e9")
        model.handle(":CALC1:MARK1:SET CENT")
        # Center should now be 2.5 GHz, span still 2 GHz
        assert float(model.handle(":SENS1:FREQ:CENT?")) == pytest.approx(2.5e9)

    # Cyclomatic complexity: 1
    def test_marker_set_start(self, model):
        model.handle(":CALC1:MARK1:X 500e6")
        model.handle(":CALC1:MARK1:SET STAR")
        assert float(model.handle(":SENS1:FREQ:STAR?")) == pytest.approx(500e6)

    # Cyclomatic complexity: 1
    def test_marker_set_stop(self, model):
        model.handle(":CALC1:MARK1:X 4e9")
        model.handle(":CALC1:MARK1:SET STOP")
        assert float(model.handle(":SENS1:FREQ:STOP?")) == pytest.approx(4e9)

    # Cyclomatic complexity: 1
    def test_multiple_markers(self, model):
        """Can use multiple independent markers."""
        model.handle(":CALC1:MARK1:X 1e9")
        model.handle(":CALC1:MARK2:X 2e9")
        model.handle(":CALC1:MARK3:X 3e9")
        assert model.handle(":CALC1:MARK1:X?") == "1000000000.0"
        assert model.handle(":CALC1:MARK2:X?") == "2000000000.0"
        assert model.handle(":CALC1:MARK3:X?") == "3000000000.0"

    # Cyclomatic complexity: 1
    def test_marker_y_uses_selected_trace(self, model):
        model.handle(":CALC1:PAR2:DEF S21")
        model.handle(":CALC1:PAR2:SEL")
        model.handle(":CALC1:FORM MLOG")
        model.handle(":CALC1:MARK1:STAT ON")
        model.handle(":CALC1:MARK1:X 1e9")

        selected_y = model.handle(":CALC1:MARK1:Y?")

        model.handle(":CALC1:PAR1:SEL")
        trace1_y = model.handle(":CALC1:MARK1:Y?")

        assert selected_y != trace1_y


class TestLimitLines:
    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        return E5071BModel(num_ports=2)

    # Cyclomatic complexity: 1
    def test_limit_state(self, model):
        model.handle(":CALC1:LIM ON")
        assert model.handle(":CALC1:LIM?") == "1"

    # Cyclomatic complexity: 1
    def test_limit_display(self, model):
        model.handle(":CALC1:LIM:DISP ON")
        assert model.handle(":CALC1:LIM:DISP?") == "1"

    # Cyclomatic complexity: 1
    def test_limit_fail(self, model):
        assert model.handle(":CALC1:LIM:FAIL?") == "0"

    # Cyclomatic complexity: 1
    def test_limit_data(self, model):
        data = "5,0,1,1000000,1000000000,0,10"
        model.handle(f":CALC1:LIM:DATA {data}")
        assert model.handle(":CALC1:LIM:DATA?") == data

    # Cyclomatic complexity: 1
    def test_limit_offset(self, model):
        model.handle(":CALC1:LIM:OFFS:AMPL 5.0")
        assert model.handle(":CALC1:LIM:OFFS:AMPL?") == "5.0"
        model.handle(":CALC1:LIM:OFFS:STIM 1e6")
        assert model.handle(":CALC1:LIM:OFFS:STIM?") == "1000000.0"


class TestTraceMath:
    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        m = E5071BModel(num_ports=2)
        m.handle(":SENS1:SWE:POIN 11")
        m.handle(":CALC1:PAR1:DEF S11")
        m.handle(":CALC1:PAR1:SEL")
        return m

    # Cyclomatic complexity: 1
    def test_math_func(self, model):
        model.handle(":CALC1:MATH:FUNC DIVide")
        assert model.handle(":CALC1:MATH:FUNC?") == "DIVide"

    # Cyclomatic complexity: 1
    def test_math_memorize(self, model):
        model.handle(":CALC1:MATH:MEM")
        # Should not error

    # Cyclomatic complexity: 1
    def test_memory_data_sdat(self, model):
        model.handle(":CALC1:MATH:MEM")
        raw = model.handle(":CALC1:DATA:SMEM?")
        vals = raw.split(",")
        assert len(vals) == 22  # 11 points * 2

    # Cyclomatic complexity: 1
    def test_memory_data_fdat(self, model):
        model.handle(":CALC1:FORM MLOG")
        model.handle(":CALC1:MATH:MEM")
        raw = model.handle(":CALC1:DATA:FMEM?")
        vals = raw.split(",")
        assert len(vals) == 22

    # Cyclomatic complexity: 1
    def test_math_stats(self, model):
        result = model.handle(":CALC1:MATH:STAT:DATA?")
        vals = result.split(",")
        assert len(vals) == 3  # mean, std, pk-pk

    # Cyclomatic complexity: 2
    def test_math_stats_use_selected_trace(self, model):
        model.handle(":CALC1:PAR2:DEF S21")
        model.handle(":CALC1:PAR2:SEL")

        selected_stats = model.handle(":CALC1:MATH:STAT:DATA?")

        model.handle(":CALC1:PAR1:SEL")
        trace1_stats = model.handle(":CALC1:MATH:STAT:DATA?")

        stats_vals = [float(v) for v in selected_stats.split(",")]
        trace1_vals = [float(v) for v in trace1_stats.split(",")]

        assert len(stats_vals) == 3
        assert selected_stats != trace1_stats
        assert stats_vals != pytest.approx(trace1_vals)

    # Cyclomatic complexity: 1
    def test_math_memory_uses_selected_trace(self, model):
        model.handle(":CALC1:PAR2:DEF S21")
        model.handle(":CALC1:PAR2:SEL")
        model.handle(":CALC1:FORM MLOG")
        model.handle(":CALC1:MATH:MEM")

        selected_mem = model.handle(":CALC1:DATA:FMEM?")

        model.handle(":CALC1:PAR1:SEL")
        trace1_mem = model.handle(":CALC1:DATA:FMEM?")

        assert selected_mem != trace1_mem


class TestPowerExtras:
    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        return E5071BModel(num_ports=2)

    # Cyclomatic complexity: 1
    def test_port_power(self, model):
        model.handle(":SOUR1:POW:PORT1 -15.0")
        assert model.handle(":SOUR1:POW:PORT1?") == "-15.0"
        model.handle(":SOUR1:POW:PORT2 -20.0")
        assert model.handle(":SOUR1:POW:PORT2?") == "-20.0"

    # Cyclomatic complexity: 1
    def test_power_coupling(self, model):
        assert model.handle(":SOUR1:POW:PORT:COUP?") == "1"
        model.handle(":SOUR1:POW:PORT:COUP OFF")
        assert model.handle(":SOUR1:POW:PORT:COUP?") == "0"

    # Cyclomatic complexity: 1
    def test_power_slope(self, model):
        model.handle(":SOUR1:POW:SLOP 1.5")
        assert model.handle(":SOUR1:POW:SLOP?") == "1.5"

    # Cyclomatic complexity: 1
    def test_power_slope_state(self, model):
        model.handle(":SOUR1:POW:SLOP:STAT ON")
        assert model.handle(":SOUR1:POW:SLOP:STAT?") == "1"

    # Cyclomatic complexity: 1
    def test_power_start_stop(self, model):
        model.handle(":SOUR1:POW:STAR -30")
        model.handle(":SOUR1:POW:STOP 10")
        assert model.handle(":SOUR1:POW:STAR?") == "-30.0"
        assert model.handle(":SOUR1:POW:STOP?") == "10.0"


class TestPortExtension:
    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        return E5071BModel(num_ports=2)

    # Cyclomatic complexity: 1
    def test_port_ext_state_ena_path(self, model):
        """E5071B uses :SENS:CORR:EXT (no :STATe)."""
        model.handle(":SENS1:CORR:EXT ON")
        assert model.handle(":SENS1:CORR:EXT?") == "1"

    # Cyclomatic complexity: 1
    def test_port_ext_state_core_path(self, model):
        """Core path with :STATe."""
        model.handle(":SENS1:CORR:EXT:STAT ON")
        assert model.handle(":SENS1:CORR:EXT:STAT?") == "1"

    # Cyclomatic complexity: 1
    def test_port_ext_time(self, model):
        model.handle(":SENS1:CORR:EXT:PORT1:TIME 2.5e-9")
        assert model.handle(":SENS1:CORR:EXT:PORT1:TIME?") == "2.5e-09"
        model.handle(":SENS1:CORR:EXT:PORT2:TIME 3e-9")
        assert model.handle(":SENS1:CORR:EXT:PORT2:TIME?") == "3e-09"

    # Cyclomatic complexity: 1
    def test_velocity_factor(self, model):
        model.handle(":SENS1:CORR:RVEL:COAX 0.66")
        assert model.handle(":SENS1:CORR:RVEL:COAX?") == "0.66"

    # Cyclomatic complexity: 1
    def test_impedance(self, model):
        model.handle(":SENS1:CORR:IMP 75")
        assert model.handle(":SENS1:CORR:IMP?") == "75.0"


class TestTriggerExtras:
    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        return E5071BModel(num_ports=2)

    # Cyclomatic complexity: 1
    def test_trig_scope(self, model):
        model.handle(":TRIG:SCOP ALL")
        # Should not error

    # Cyclomatic complexity: 1
    def test_trig_point(self, model):
        model.handle(":TRIG:POIN ON")
        assert model.handle(":TRIG:POIN?") == "1"

    # Cyclomatic complexity: 1
    def test_trig_source_query(self, model):
        model.handle(":TRIG:SOUR BUS")
        assert model.handle(":TRIG:SOUR?") == "BUS"


class TestServiceQueries:
    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        return E5071BModel(num_ports=2)

    # Cyclomatic complexity: 1
    def test_serv_trace_count(self, model):
        assert model.handle(":SERV:CHAN:TRAC:COUN?") == "1"

    # Cyclomatic complexity: 1
    def test_serv_active_channel(self, model):
        assert model.handle(":SERV:CHAN:ACT?") == "1"

    # Cyclomatic complexity: 1
    def test_serv_active_trace(self, model):
        assert model.handle(":SERV:CHAN:TRAC:ACT?") == "1"

    # Cyclomatic complexity: 1
    def test_serv_freq_max(self, model):
        assert model.handle(":SERV:SWE:FREQ:MAX?") == "8500000000"

    # Cyclomatic complexity: 1
    def test_serv_freq_min(self, model):
        assert model.handle(":SERV:SWE:FREQ:MIN?") == "300000"

    # Cyclomatic complexity: 1
    def test_serv_swp_points(self, model):
        assert model.handle(":SERV:SWE:POIN?") == "1601"

    # Cyclomatic complexity: 1
    def test_seg_count(self, model):
        seg = "5,2,1,1e6,1e9,101,1000,0,1e9,3e9,201,1000,0"
        model.handle(f":SENS1:SEGM:DATA {seg}")
        assert model.handle(":SENS1:SEGM:COUN?") == "2"


class TestSNA5000NewFeatures:
    """Test the new features on the SNA5000 model too."""

    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self):
        return SNA5000Model(num_ports=2)

    # Cyclomatic complexity: 1
    def test_ieee_488_cls(self, model):
        assert model.handle("*CLS") is None

    # Cyclomatic complexity: 1
    def test_ieee_488_ese(self, model):
        model.handle("*ESE 128")
        assert model.handle("*ESE?") == "128"

    # Cyclomatic complexity: 1
    def test_sys_err(self, model):
        assert model.handle(":SYST:ERR?") == '0,"No error"'

    # Cyclomatic complexity: 1
    def test_output(self, model):
        model.handle(":OUTP OFF")
        assert model.handle(":OUTP?") == "0"

    # Cyclomatic complexity: 1
    def test_freq_center_span(self, model):
        model.handle(":SENS1:FREQ:STAR 1e9")
        model.handle(":SENS1:FREQ:STOP 3e9")
        assert model.handle(":SENS1:FREQ:CENT?") == "2000000000.0"
        assert model.handle(":SENS1:FREQ:SPAN?") == "2000000000.0"

    # Cyclomatic complexity: 1
    def test_sweep_delay(self, model):
        model.handle(":SENS1:SWE:DEL 0.01")
        assert model.handle(":SENS1:SWE:DEL?") == "0.01"

    # Cyclomatic complexity: 1
    def test_avg_count_set(self, model):
        model.handle(":SENS1:AVER:COUN 8")
        assert model.handle(":SENS1:AVER:COUN?") == "8"

    # Cyclomatic complexity: 1
    def test_avg_clear(self, model):
        assert model.handle(":CALC1:AVER:CLE") is None

    # Cyclomatic complexity: 1
    def test_avg_type(self, model):
        model.handle(":CALC1:AVER:TYP SWE")
        assert model.handle(":CALC1:AVER:TYP?") == "SWE"

    # Cyclomatic complexity: 1
    def test_elec_delay(self, model):
        model.handle(":CALC1:CORR:EDEL:TIME 1e-9")
        assert model.handle(":CALC1:CORR:EDEL:TIME?") == "1e-09"

    # Cyclomatic complexity: 1
    def test_markers(self, model):
        model.handle(":SENS1:SWE:POIN 101")
        model.handle(":CALC1:PAR1:DEF S11")
        model.handle(":CALC1:PAR1:SEL")
        model.handle(":CALC1:MARK1:STAT ON")
        assert model.handle(":CALC1:MARK1:STAT?") == "1"
        model.handle(":CALC1:MARK1:X 1.5e9")
        assert model.handle(":CALC1:MARK1:X?") == "1500000000.0"
        result = model.handle(":CALC1:MARK1:Y?")
        assert "," in result

    # Cyclomatic complexity: 1
    def test_marker_search(self, model):
        model.handle(":SENS1:SWE:POIN 101")
        model.handle(":CALC1:PAR1:DEF S11")
        model.handle(":CALC1:PAR1:SEL")
        model.handle(":CALC1:MARK1:STAT ON")
        model.handle(":CALC1:MARK1:FUNC:TYPE MAXimum")
        model.handle(":CALC1:MARK1:FUNC:EXEC")
        x = float(model.handle(":CALC1:MARK1:X?"))
        assert x > 0

    # Cyclomatic complexity: 1
    def test_marker_set_center(self, model):
        model.handle(":CALC1:MARK1:X 2e9")
        model.handle(":CALC1:MARK1:SET:CENT")

    # Cyclomatic complexity: 1
    def test_limit_lines(self, model):
        model.handle(":CALC1:LIM:STAT ON")
        assert model.handle(":CALC1:LIM:STAT?") == "1"
        assert model.handle(":CALC1:LIM:FAIL?") == "0"

    # Cyclomatic complexity: 1
    def test_math_func(self, model):
        model.handle(":CALC1:MATH:FUNC NORMal")
        assert model.handle(":CALC1:MATH:FUNC?") == "NORMal"

    # Cyclomatic complexity: 1
    def test_port_power(self, model):
        model.handle(":SOUR1:POW:PORT1 -10")
        assert model.handle(":SOUR1:POW:PORT1?") == "-10.0"

    # Cyclomatic complexity: 1
    def test_power_coupling(self, model):
        model.handle(":SOUR1:POW:PORT:COUP OFF")
        assert model.handle(":SOUR1:POW:PORT:COUP?") == "0"

    # Cyclomatic complexity: 1
    def test_port_ext(self, model):
        model.handle(":SENS1:CORR:EXT:STAT ON")
        assert model.handle(":SENS1:CORR:EXT:STAT?") == "1"

    # Cyclomatic complexity: 1
    def test_trig_point(self, model):
        model.handle(":TRIG:POIN ON")
        assert model.handle(":TRIG:POIN?") == "1"

    # Cyclomatic complexity: 1
    def test_trig_source_query(self, model):
        model.handle(":TRIG:SEQ:SOUR BUS")
        assert model.handle(":TRIG:SEQ:SOUR?") == "BUS"

    # Cyclomatic complexity: 1
    def test_seg_total_points(self, model):
        assert model.handle(":SENS1:SEGM:SWE:POIN?") is not None

    # Cyclomatic complexity: 1
    def test_seg_total_points_come_from_segment_data(self, model):
        seg = "5,2,1,1e6,1e9,101,1000,0,1e9,3e9,201,1000,0"
        model.handle(f":SENS1:SEGM:DATA {seg}")
        assert model.handle(":SENS1:SEGM:SWE:POIN?") == "302"


class TestProxyNewFeatures:
    """Test new features through the proxy layer."""

    pytest.importorskip("vnasim.backend.client")

    @pytest.fixture
    # Cyclomatic complexity: 1
    def backend_server(self):
        import asyncio
        import socket
        import threading
        from vnasim.server import start_instrument

        model = SNA5000Model(num_ports=2)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        ready = threading.Event()

        # Cyclomatic complexity: 1
        def run():
            # Cyclomatic complexity: 1
            async def start():
                await start_instrument(model, port=port, name="backend",
                                       host="127.0.0.1")
                ready.set()
                await asyncio.Event().wait()
            asyncio.run(start())

        t = threading.Thread(target=run, daemon=True)
        t.start()
        ready.wait(timeout=5)
        yield port

    @pytest.fixture
    # Cyclomatic complexity: 1
    def model(self, backend_server):
        from vnasim.backend.client import BackendClient
        from vnasim.backend.translator import SNA5000Translator
        from vnasim.models.proxy import ProxyVNAModel
        from vnasim.models.mixins import ENACommandsMixin

        class ProxyE5071B(ProxyVNAModel, ENACommandsMixin):
            # Cyclomatic complexity: 1
            def _build_tree(self):
                self._register_core()
                self._register_ena()

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

    # Cyclomatic complexity: 1
    def test_freq_center_forwarded(self, model):
        model.handle(":SENS1:FREQ:STAR 1e9")
        model.handle(":SENS1:FREQ:STOP 3e9")
        model.handle(":SENS1:FREQ:CENT 2e9")
        resp = model.handle(":SENS1:FREQ:CENT?")
        assert float(resp) == pytest.approx(2e9)

    # Cyclomatic complexity: 1
    def test_freq_span_forwarded(self, model):
        model.handle(":SENS1:FREQ:STAR 1e9")
        model.handle(":SENS1:FREQ:STOP 3e9")
        model.handle(":SENS1:FREQ:SPAN 1e9")
        resp = model.handle(":SENS1:FREQ:SPAN?")
        assert float(resp) == pytest.approx(1e9)

    # Cyclomatic complexity: 1
    def test_sweep_delay_forwarded(self, model):
        model.handle(":SENS1:SWE:DEL 0.005")
        resp = model.handle(":SENS1:SWE:DEL?")
        assert float(resp) == pytest.approx(0.005)
        assert model._channels[1].sweep_delay == pytest.approx(0.005)

    # Cyclomatic complexity: 1
    def test_avg_count_forwarded(self, model):
        model.handle(":SENS1:AVER:COUN 4")
        assert model.handle(":SENS1:AVER:COUN?") == "4"
        assert model._channels[1].avg_count == 4

    # Cyclomatic complexity: 1
    def test_avg_clear_forwarded(self, model):
        model.handle(":SENS1:AVER:CLE")

    # Cyclomatic complexity: 1
    def test_elec_delay_forwarded(self, model):
        model.handle(":CALC1:CORR:EDEL:TIME 2e-9")
        resp = model.handle(":CALC1:CORR:EDEL:TIME?")
        assert float(resp) == pytest.approx(2e-9)
        assert model._channels[1].elec_delay == pytest.approx(2e-9)

    # Cyclomatic complexity: 1
    def test_output_forwarded(self, model):
        model.handle(":OUTP OFF")
        assert model.handle(":OUTP?") == "0"
        assert model._output_state is False
        model.handle(":OUTP ON")
        assert model.handle(":OUTP?") == "1"
        assert model._output_state is True

    # Cyclomatic complexity: 1
    def test_port_ext_forwarded(self, model):
        model.handle(":SENS1:CORR:EXT:STAT ON")
        assert model.handle(":SENS1:CORR:EXT:STAT?") == "1"

    # Cyclomatic complexity: 1
    def test_impedance_forwarded(self, model):
        model.handle(":SENS1:CORR:IMP 75")
        assert model.handle(":SENS1:CORR:IMP?") == "75.0"

    # Cyclomatic complexity: 1
    def test_backend_helpers_ignore_local_only_channels(self, model):
        model._backend_set_measurement(2, "S11")
        model._backend_trigger(2)

    # Cyclomatic complexity: 1
    def test_freq_center_updates_frontend_cache(self, model):
        model.handle(":SENS1:FREQ:STAR 1e9")
        model.handle(":SENS1:FREQ:STOP 3e9")
        model.handle(":SENS1:FREQ:CENT 2.5e9")

        assert model._channels[1].start_freq == pytest.approx(1.5e9)
        assert model._channels[1].stop_freq == pytest.approx(3.5e9)

    # Cyclomatic complexity: 1
    def test_marker_set_center_updates_frontend_cache(self, model):
        model.handle(":SENS1:FREQ:STAR 1e9")
        model.handle(":SENS1:FREQ:STOP 3e9")
        model.handle(":CALC1:MARK1:X 2.5e9")
        model.handle(":CALC1:MARK1:SET CENT")

        assert model._channels[1].start_freq == pytest.approx(1.5e9)
        assert model._channels[1].stop_freq == pytest.approx(3.5e9)

    # Cyclomatic complexity: 1
    def test_marker_set_rlevel_updates_frontend_cache(self, model):
        model.handle(":SENS1:SWE:POIN 101")
        model.handle(":CALC1:PAR1:DEF S11")
        model.handle(":CALC1:PAR1:SEL")
        model.handle(":CALC1:FORM MLOG")
        model.handle(":CALC1:MARK1:X 1e9")
        expected_rlevel = float(model.handle(":CALC1:MARK1:Y?").split(",")[0])
        model.handle(":CALC1:MARK1:SET RLEV")

        assert float(model.handle(":DISP:WIND1:TRAC1:Y:RLEV?")) == pytest.approx(
            expected_rlevel
        )
