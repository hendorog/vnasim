"""Tests for the SCPI tree parser."""

import pytest

from vnasim.scpi.parser import SCPITree, _extract_forms, _match_keyword
from vnasim.scpi.types import Unhandled


class TestExtractForms:
    def test_sense(self):
        assert _extract_forms("SENSe") == ("SENS", "SENSE")

    def test_frequency(self):
        assert _extract_forms("FREQuency") == ("FREQ", "FREQUENCY")

    def test_all_upper(self):
        assert _extract_forms("DATA") == ("DATA", "DATA")

    def test_corrdata(self):
        assert _extract_forms("CORRdata") == ("CORR", "CORRDATA")

    def test_rawdata(self):
        assert _extract_forms("RAWData") == ("RAWD", "RAWDATA")

    def test_start(self):
        assert _extract_forms("STARt") == ("STAR", "START")

    def test_selected(self):
        assert _extract_forms("SELected") == ("SEL", "SELECTED")

    def test_rlevel(self):
        assert _extract_forms("RLEVel") == ("RLEV", "RLEVEL")


class TestMatchKeyword:
    def test_short_form(self):
        assert _match_keyword("SENS", "SENS", "SENSE")

    def test_full_form(self):
        assert _match_keyword("SENSE", "SENS", "SENSE")

    def test_case_insensitive(self):
        assert _match_keyword("sens", "SENS", "SENSE")
        assert _match_keyword("Sense", "SENS", "SENSE")

    def test_too_short(self):
        assert not _match_keyword("SEN", "SENS", "SENSE")

    def test_too_long(self):
        assert not _match_keyword("SENSEX", "SENS", "SENSE")

    def test_partial_valid(self):
        assert _match_keyword("SENSI", "SENS", "SENSE") is False
        # Only prefixes of full form are valid
        # "SENSI" is not a prefix of "SENSE"

    def test_frequency_forms(self):
        assert _match_keyword("FREQ", "FREQ", "FREQUENCY")
        assert _match_keyword("FREQU", "FREQ", "FREQUENCY")
        assert _match_keyword("FREQUENCY", "FREQ", "FREQUENCY")


class TestSCPITree:
    @pytest.fixture
    def tree(self):
        t = SCPITree()
        results = {}

        def make_handler(name):
            def h(cmd):
                results["last"] = (name, cmd.is_query, cmd.arguments,
                                   cmd.suffixes)
                return f"OK:{name}" if cmd.is_query else None
            return h

        t.register("*IDN", query_handler=make_handler("idn"))
        t.register("*RST", set_handler=make_handler("rst"))
        t.register("*OPC", query_handler=make_handler("opc"))
        t.register(":SENSe#:FREQuency:STARt", handler=make_handler("freq_start"))
        t.register(":SENSe#:FREQuency:STOP", handler=make_handler("freq_stop"))
        t.register(":SENSe#:FREQuency:DATA", query_handler=make_handler("freq_data"))
        t.register(":SENSe#:SWEep:POINts", handler=make_handler("swp_points"))
        t.register(":CALCulate#:PARameter#:DEFine",
                   handler=make_handler("calc_par_def"))
        t.register(":DISPlay:CHANnel:LIST",
                   query_handler=make_handler("chan_list"))
        t.register(":DISPlay:CHANnel#:TRACe:LIST",
                   query_handler=make_handler("chan_trace_list"))
        t.register(":DISPlay:TRACe:LIST",
                   query_handler=make_handler("trace_list"))
        t.register(":DISPlay:TRACe#:ACTivate",
                   set_handler=make_handler("trace_activate"))
        t.register(":SENSe#:DATA:CORRdata",
                   query_handler=make_handler("data_corr"))

        return t, results

    def test_idn_query(self, tree):
        t, r = tree
        resp = t.dispatch("*IDN?")
        assert resp == "OK:idn"
        assert r["last"][0] == "idn"
        assert r["last"][1] is True

    def test_rst_set(self, tree):
        t, r = tree
        resp = t.dispatch("*RST")
        assert resp is None
        assert r["last"][0] == "rst"

    def test_opc_query(self, tree):
        t, r = tree
        resp = t.dispatch("*OPC?")
        assert resp == "OK:opc"

    def test_freq_start_query(self, tree):
        t, r = tree
        resp = t.dispatch(":SENSe1:FREQuency:STARt?")
        assert resp == "OK:freq_start"
        assert r["last"][3] == [1]  # suffixes

    def test_freq_start_set(self, tree):
        t, r = tree
        resp = t.dispatch(":SENSe1:FREQuency:STARt 1000000.0")
        assert resp is None
        assert r["last"][2] == "1000000.0"  # arguments
        assert r["last"][3] == [1]

    def test_freq_start_channel2(self, tree):
        t, r = tree
        t.dispatch(":SENSe2:FREQuency:STARt?")
        assert r["last"][3] == [2]

    def test_short_form_matching(self, tree):
        t, r = tree
        t.dispatch(":SENS1:FREQ:STAR?")
        assert r["last"][0] == "freq_start"

    def test_full_form_matching(self, tree):
        t, r = tree
        t.dispatch(":SENSE1:FREQUENCY:START?")
        assert r["last"][0] == "freq_start"

    def test_case_insensitive(self, tree):
        t, r = tree
        t.dispatch(":sense1:frequency:start?")
        assert r["last"][0] == "freq_start"

    def test_calc_parameter_two_suffixes(self, tree):
        t, r = tree
        t.dispatch(":CALCulate2:PARameter3:DEFine S21")
        assert r["last"][0] == "calc_par_def"
        assert r["last"][2] == "S21"
        assert r["last"][3] == [2, 3]  # channel=2, trace=3

    def test_default_suffix(self, tree):
        """No suffix defaults to 1."""
        t, r = tree
        t.dispatch(":SENSe:FREQuency:STARt?")
        assert r["last"][3] == [1]

    def test_display_fixed_vs_suffix(self, tree):
        """Verify fixed children (CHANnel:LIST) vs suffix children (CHANnel#:TRACe:LIST)."""
        t, r = tree
        t.dispatch(":DISPlay:CHANnel:LIST?")
        assert r["last"][0] == "chan_list"

        t.dispatch(":DISPlay:CHANnel1:TRACe:LIST?")
        assert r["last"][0] == "chan_trace_list"
        assert r["last"][3] == [1]

    def test_trace_fixed_vs_suffix(self, tree):
        t, r = tree
        t.dispatch(":DISPlay:TRACe:LIST?")
        assert r["last"][0] == "trace_list"

        t.dispatch(":DISPlay:TRACe2:ACTivate")
        assert r["last"][0] == "trace_activate"
        assert r["last"][3] == [2]

    def test_query_with_arguments(self, tree):
        t, r = tree
        t.dispatch(':SENSe1:DATA:CORRdata? S21')
        assert r["last"][0] == "data_corr"
        assert r["last"][2] == "S21"
        assert r["last"][1] is True

    def test_query_with_quoted_arguments(self, tree):
        t, r = tree
        t.dispatch(':SENSe1:DATA:CORRdata? "a2/b2,1"')
        assert r["last"][2] == '"a2/b2,1"'

    def test_unrecognized_command(self, tree):
        t, r = tree
        resp = t.dispatch(":BOGUS:COMMAND?")
        assert isinstance(resp, Unhandled)
        assert resp.reason == "no matching command path"

    def test_unhandled_wrong_direction(self, tree):
        t, r = tree
        # *IDN is query-only; sending it as a set should be unhandled
        resp = t.dispatch("*IDN")
        assert isinstance(resp, Unhandled)
        assert "no set handler" in resp.reason

    def test_sweep_points(self, tree):
        t, r = tree
        t.dispatch(":SENSe1:SWEep:POINts 201")
        assert r["last"][0] == "swp_points"
        assert r["last"][2] == "201"
