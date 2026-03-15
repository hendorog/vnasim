"""Tests for the SNA5000 VNA model."""

import pytest

from vnasim.models.sna5000 import SNA5000Model
from vnasim.scpi.types import Unhandled


class TestSNA5000Model:
    @pytest.fixture
    def model(self):
        return SNA5000Model(num_ports=2, idn="Siglent Technologies,SNA5012A,TEST,1.0")

    def test_idn(self, model):
        assert model.handle("*IDN?") == "Siglent Technologies,SNA5012A,TEST,1.0"

    def test_opc(self, model):
        assert model.handle("*OPC?") == "1"

    def test_rst(self, model):
        model.handle(":SENSe1:FREQuency:STARt 500e6")
        model.handle("*RST")
        assert model.handle(":SENSe1:FREQuency:STARt?") == str(100e6)

    def test_freq_start_set_query(self, model):
        model.handle(":SENSe1:FREQuency:STARt 1000000.0")
        assert model.handle(":SENSe1:FREQuency:STARt?") == "1000000.0"

    def test_freq_stop_set_query(self, model):
        model.handle(":SENSe1:FREQuency:STOP 6000000000.0")
        assert model.handle(":SENSe1:FREQuency:STOP?") == "6000000000.0"

    def test_freq_data(self, model):
        model.handle(":SENSe1:FREQuency:STARt 1e6")
        model.handle(":SENSe1:FREQuency:STOP 6e9")
        model.handle(":SENSe1:SWEep:POINts 5")
        raw = model.handle(":SENSe1:FREQuency:DATA?")
        freqs = [float(x) for x in raw.split(",")]
        assert len(freqs) == 5
        assert freqs[0] == pytest.approx(1e6)
        assert freqs[-1] == pytest.approx(6e9)

    def test_cw_freq(self, model):
        model.handle(":SENSe1:FREQuency:CW 2.5e9")
        assert model.handle(":SENSe1:FREQuency:CW?") == "2500000000.0"

    def test_sweep_points(self, model):
        model.handle(":SENSe1:SWEep:POINts 201")
        assert model.handle(":SENSe1:SWEep:POINts?") == "201"

    def test_sweep_type(self, model):
        model.handle(":SENSe1:SWEep:TYPE LINear")
        assert model.handle(":SENSe1:SWEep:TYPE?") == "LINear"
        model.handle(":SENSe1:SWEep:TYPE SEGMent")
        assert model.handle(":SENSe1:SWEep:TYPE?") == "SEGMent"

    def test_sweep_time(self, model):
        model.handle(":SENSe1:SWEep:TIME 0.5")
        assert model.handle(":SENSe1:SWEep:TIME?") == "0.5"

    def test_sweep_time_auto(self, model):
        # Should not raise
        model.handle(":SENSe1:SWEep:TIME:AUTO OFF")

    def test_ifbw(self, model):
        model.handle(":SENSe1:BANDwidth:RESolution 3000.0")
        assert model.handle(":SENSe1:BANDwidth:RESolution?") == "3000.0"

    def test_source_power(self, model):
        model.handle(":SOURce1:POWer -10.0")
        assert model.handle(":SOURce1:POWer?") == "-10.0"

    def test_averaging(self, model):
        assert model.handle(":SENSe1:AVERage:STATe?") == "OFF"
        model.handle(":SENSe1:AVERage:STATe ON")
        assert model.handle(":SENSe1:AVERage:STATe?") == "ON"
        assert model.handle(":SENSe1:AVERage:COUNt?") == "1"

    def test_smoothing(self, model):
        assert model.handle(":CALCulate1:SMOothing:STATe?") == "OFF"
        model.handle(":CALCulate1:SMOothing:STATe ON")
        assert model.handle(":CALCulate1:SMOothing:STATe?") == "ON"
        model.handle(":CALCulate1:SMOothing:APERture 10.0")
        assert model.handle(":CALCulate1:SMOothing:APERture?") == "10.0"

    def test_correction_state(self, model):
        assert model.handle(":SENSe1:CORRection:STATe?") == "OFF"
        model.handle(":SENSe1:CORRection:STATe ON")
        assert model.handle(":SENSe1:CORRection:STATe?") == "ON"

    def test_display_scale(self, model):
        model.handle(":DISPlay:WINDow1:TRACe1:Y:SCALe:RLEVel -20.0")
        assert model.handle(":DISPlay:WINDow1:TRACe1:Y:SCALe:RLEVel?") == "-20.0"
        model.handle(":DISPlay:WINDow1:TRACe1:Y:SCALe:PDIVision 5.0")
        assert model.handle(":DISPlay:WINDow1:TRACe1:Y:SCALe:PDIVision?") == "5.0"
        model.handle(":DISPlay:WINDow1:TRACe1:Y:SCALe:RPOSition 3")
        assert model.handle(":DISPlay:WINDow1:TRACe1:Y:SCALe:RPOSition?") == "3"

    def test_trace_define_and_select(self, model):
        model.handle(":CALCulate1:PARameter1:DEFine S21")
        assert model.handle(":CALCulate1:PARameter1:DEFine?") == "S21"
        model.handle(":CALCulate1:PARameter1:SELect")

    def test_trace_define_expression(self, model):
        model.handle(':CALCulate1:PARameter1:DEFine "a2/b2,1"')
        assert model.handle(":CALCulate1:PARameter1:DEFine?") == "a2/b2,1"

    def test_data_corrected(self, model):
        model.handle(":SENSe1:SWEep:POINts 11")
        raw = model.handle(":SENSe1:DATA:CORRdata? S21")
        vals = raw.split(",")
        # 11 points, re+im pairs = 22 values
        assert len(vals) == 22

    def test_data_raw(self, model):
        model.handle(":SENSe1:SWEep:POINts 11")
        raw = model.handle(":SENSe1:DATA:RAWData? S11")
        vals = raw.split(",")
        assert len(vals) == 22

    def test_data_corrected_quoted_expression(self, model):
        model.handle(":SENSe1:SWEep:POINts 5")
        raw = model.handle(':SENSe1:DATA:CORRdata? "a2/b2,1"')
        vals = raw.split(",")
        assert len(vals) == 10

    def test_selected_sdata(self, model):
        model.handle(":SENSe1:SWEep:POINts 5")
        model.handle(":CALCulate1:PARameter1:DEFine S21")
        model.handle(":CALCulate1:PARameter1:SELect")
        raw = model.handle(":CALCulate1:SELected:DATA:SDATa?")
        vals = raw.split(",")
        assert len(vals) == 10

    def test_selected_fdata(self, model):
        model.handle(":SENSe1:SWEep:POINts 5")
        model.handle(":CALCulate1:PARameter1:DEFine S11")
        model.handle(":CALCulate1:PARameter1:SELect")
        model.handle(":CALCulate1:SELected:FORMat MLOGarithmic")
        raw = model.handle(":CALCulate1:SELected:DATA:FDATa?")
        vals = raw.split(",")
        # 5 points, re+im pairs = 10 values
        assert len(vals) == 10
        # For MLOGarithmic, imaginary values should be "0"
        for i in range(1, len(vals), 2):
            assert vals[i] == "0"

    def test_channel_list(self, model):
        assert model.handle(":DISPlay:CHANnel:LIST?") == "1"
        model.handle(":DISPlay:ADD:FUNCtion:EXECute WIN_CH_TRC")
        assert model.handle(":DISPlay:CHANnel:LIST?") == "1,2"

    def test_trace_list(self, model):
        assert model.handle(":DISPlay:TRACe:LIST?") == "1"
        model.handle(":DISPlay:ADD:FUNCtion:EXECute CH_TRC")
        assert model.handle(":DISPlay:TRACe:LIST?") == "1,2"

    def test_channel_trace_list(self, model):
        assert model.handle(":DISPlay:CHANnel1:TRACe:LIST?") == "1"

    def test_trigger_commands(self, model):
        # All trigger commands should succeed without errors
        model.handle(":DISPlay:TRACe1:ACTivate")
        model.handle(":INITiate1:CONTinuous ON")
        model.handle(":TRIGger:SCOPe ACTive")
        model.handle(":TRIGger:SEQuence:SOURce BUS")
        model.handle(":TRIGger:SEQuence:SING")

    def test_multi_channel_isolation(self, model):
        """Channels maintain independent state."""
        model.handle(":SENSe1:FREQuency:STARt 1e6")
        model.handle(":SENSe2:FREQuency:STARt 500e6")
        assert model.handle(":SENSe1:FREQuency:STARt?") == "1000000.0"
        assert model.handle(":SENSe2:FREQuency:STARt?") == "500000000.0"

    def test_correction_coefficients(self, model):
        model.handle(":SENSe1:SWEep:POINts 3")
        # Query ideal coefficient
        raw = model.handle(":SENSe1:CORRection:COEFficient:DATA? ED,1,1")
        vals = [float(x) for x in raw.split(",")]
        # ED (directivity) ideal = zeros: 3 points * 2 values = 6
        assert len(vals) == 6
        assert all(v == 0.0 for v in vals)

        # ER (reflection tracking) ideal = ones
        raw = model.handle(":SENSe1:CORRection:COEFficient:DATA? ER,1,1")
        vals = [float(x) for x in raw.split(",")]
        assert vals[0] == 1.0  # real part of first point
        assert vals[1] == 0.0  # imag part of first point

    def test_correction_coef_upload(self, model):
        model.handle(":SENSe1:SWEep:POINts 2")
        model.handle(
            ":SENSe1:CORRection:COEFficient:DATA ED,1,1,0.01,0.02,0.03,0.04"
        )
        raw = model.handle(":SENSe1:CORRection:COEFficient:DATA? ED,1,1")
        vals = [float(x) for x in raw.split(",")]
        assert vals == pytest.approx([0.01, 0.02, 0.03, 0.04])

    def test_correction_methods_accepted(self, model):
        # All cal method commands should be accepted (no-ops)
        model.handle(":SENSe1:CORRection:COEFficient:METHod:RESPonse:OPEN 1")
        model.handle(":SENSe1:CORRection:COEFficient:METHod:RESPonse:SHORt 1")
        model.handle(":SENSe1:CORRection:COEFficient:METHod:RESPonse:THRU 2,1")
        model.handle(":SENSe1:CORRection:COEFficient:METHod:ERESponse 1,2")
        model.handle(":SENSe1:CORRection:COEFficient:METHod:SOLT1 1,1")
        model.handle(":SENSe1:CORRection:COEFficient:METHod:SOLT2 1,2")
        model.handle(":SENSe1:CORRection:COEFficient:SAVE")

    def test_segment_data(self, model):
        seg = "5,0,1,1,0,0,1,1e6,6e9,201,1000,0"
        model.handle(f":SENSe1:SEGMent:DATA {seg}")
        assert model.handle(":SENSe1:SEGMent:DATA?") == seg

    def test_balanced_topology(self, model):
        model.handle(":CALCulate1:DTOPology B,1,2")
        assert model.handle(":CALCulate1:DTOPology?") == "B,1,2"

    def test_short_form_commands(self, model):
        """Verify short-form SCPI matching works through the model."""
        model.handle(":SENS1:FREQ:STAR 2e9")
        assert model.handle(":SENS1:FREQ:STAR?") == "2000000000.0"

    def test_unrecognized_command_returns_unhandled(self, model):
        result = model.handle(":BOGUS:COMMAND?")
        assert isinstance(result, Unhandled)
        assert "no matching command path" in result.reason

    def test_4port_model(self):
        model = SNA5000Model(num_ports=4)
        model.handle(":SENSe1:SWEep:POINts 5")
        # S41 should work for 4-port
        raw = model.handle(":SENSe1:DATA:CORRdata? S41")
        vals = raw.split(",")
        assert len(vals) == 10
