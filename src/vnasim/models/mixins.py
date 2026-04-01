"""Registration mixins — each registers a group of SCPI commands.

Mixins only register commands on ``self._tree`` and define any
handler methods unique to that group. Shared handler methods
live in :class:`~vnasim.models.common.CommonVNAModel`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from vnasim.scpi.types import ParsedCommand


# =====================================================================
# Siglent SNA5000 commands
# =====================================================================

class SiglentCommandsMixin:
    """Siglent SNA5000A-specific SCPI paths (full-length keywords)."""

    def _register_siglent(self) -> None:
        t = self._tree

        # IFBW with :RESolution
        t.register(":SENSe#:BANDwidth:RESolution", handler=self._handle_ifbw)

        # Sweep type (full keyword TYPE)
        t.register(":SENSe#:SWEep:TYPE", handler=self._handle_swp_type)

        # Averaging with :STATe + count + clear + type
        t.register(":SENSe#:AVERage:STATe", handler=self._handle_avg_state)
        t.register(":SENSe#:AVERage:COUNt", handler=self._handle_avg_count)
        t.register(":CALCulate#:AVERage:CLEar",
                   set_handler=self._handle_avg_clear)
        t.register(":CALCulate#:AVERage:TYPe",
                   handler=self._handle_avg_type)

        # Smoothing with :STATe
        t.register(":CALCulate#:SMOothing:STATe", handler=self._handle_smooth_state)
        t.register(":CALCulate#:SMOothing:APERture",
                   handler=self._handle_smooth_aperture)

        # Trace parameter definition
        t.register(":CALCulate#:PARameter#:DEFine",
                   handler=self._handle_calc_par_def)
        t.register(":CALCulate#:PARameter#:SELect",
                   set_handler=self._handle_calc_par_sel)

        # Selected trace data
        t.register(":CALCulate#:SELected:FORMat",
                   set_handler=self._handle_calc_sel_fmt)
        t.register(":CALCulate#:SELected:DATA:FDATa",
                   query_handler=self._handle_calc_sel_fdata)
        t.register(":CALCulate#:SELected:DATA:SDATa",
                   query_handler=self._handle_calc_sel_sdata)

        # Raw/corrected data
        t.register(":SENSe#:DATA:RAWData", query_handler=self._handle_data_raw)
        t.register(":SENSe#:DATA:CORRdata", query_handler=self._handle_data_corr)

        # Frequency list
        t.register(":SENSe#:FREQuency:DATA", query_handler=self._handle_freq_data)

        # Electrical delay (SNA5000: CALC:CORR:EDELay:TIME)
        t.register(":CALCulate#:CORRection:EDELay:TIME",
                   handler=self._handle_elec_delay)

        # Markers (SNA5000: CALC:MARK{1-15})
        t.register(":CALCulate#:MARKer#:STATe",
                   handler=self._handle_marker_state)
        t.register(":CALCulate#:MARKer#:ACTivate",
                   set_handler=self._handle_marker_activate)
        t.register(":CALCulate#:MARKer#:X", handler=self._handle_marker_x)
        t.register(":CALCulate#:MARKer#:Y",
                   query_handler=self._handle_marker_y)
        t.register(":CALCulate#:MARKer#:DISCrete",
                   handler=self._handle_marker_discrete)
        t.register(":CALCulate#:MARKer#:COUPle",
                   handler=self._handle_marker_coupling)
        t.register(":CALCulate#:MARKer#:REFerence:STATe",
                   handler=self._handle_marker_ref_state)
        t.register(":CALCulate#:MARKer#:REFerence:X",
                   handler=self._handle_marker_ref_x)
        t.register(":CALCulate#:MARKer#:REFerence:Y",
                   query_handler=self._handle_marker_ref_y)
        t.register(":CALCulate#:MARKer#:SET:CENTer",
                   set_handler=self._handle_marker_set_center)
        t.register(":CALCulate#:MARKer#:SET:STARt",
                   set_handler=self._handle_marker_set_start)
        t.register(":CALCulate#:MARKer#:SET:STOP",
                   set_handler=self._handle_marker_set_stop)
        t.register(":CALCulate#:MARKer#:SET:RLEVel",
                   set_handler=self._handle_marker_set_rlevel)
        t.register(":CALCulate#:MARKer#:SET:DELay",
                   set_handler=self._handle_marker_set_delay)
        t.register(":CALCulate#:MARKer#:FUNCtion:TYPE",
                   handler=self._handle_marker_func_type)
        t.register(":CALCulate#:MARKer#:FUNCtion:EXECute",
                   set_handler=self._handle_marker_func_exec)
        t.register(":CALCulate#:MARKer#:FUNCtion:TARGet",
                   handler=self._handle_marker_func_target)
        t.register(":CALCulate#:MARKer#:FUNCtion:TTRansition",
                   handler=self._handle_marker_func_ttrans)
        t.register(":CALCulate#:MARKer#:FUNCtion:TRACking",
                   handler=self._handle_marker_func_tracking)
        t.register(":CALCulate#:MARKer#:FUNCtion:DOMain:STATe",
                   handler=self._handle_marker_func_domain_state)
        t.register(":CALCulate#:MARKer#:FUNCtion:DOMain:STARt",
                   handler=self._handle_marker_func_domain_start)
        t.register(":CALCulate#:MARKer#:FUNCtion:DOMain:STOP",
                   handler=self._handle_marker_func_domain_stop)
        t.register(":CALCulate#:MARKer#:FUNCtion:MULTi:TYPE",
                   handler=self._handle_marker_func_type)
        t.register(":CALCulate#:MARKer#:FUNCtion:MULTi:EXECute",
                   set_handler=self._handle_marker_func_exec)
        t.register(":CALCulate#:MARKer#:FUNCtion:MULTi:TRACking",
                   handler=self._handle_marker_func_tracking)

        # Limit lines (SNA5000: CALC:LIMit)
        t.register(":CALCulate#:LIMit:STATe",
                   handler=self._handle_limit_state)
        t.register(":CALCulate#:LIMit:DISPlay:STATe",
                   handler=self._handle_limit_display)
        t.register(":CALCulate#:LIMit:FAIL",
                   query_handler=self._handle_limit_fail)
        t.register(":CALCulate#:LIMit:REPort:ALL",
                   query_handler=self._handle_limit_report_all)
        t.register(":CALCulate#:LIMit:REPort:DATA",
                   query_handler=self._handle_limit_report_data)
        t.register(":CALCulate#:LIMit:REPort:POINts",
                   query_handler=self._handle_limit_report_points)
        t.register(":CALCulate#:LIMit:DATA", handler=self._handle_limit_data)
        t.register(":CALCulate#:LIMit:UPPer:DATA",
                   handler=self._handle_limit_data)
        t.register(":CALCulate#:LIMit:LOWer:DATA",
                   handler=self._handle_limit_data)
        t.register(":CALCulate#:LIMit:CLEar",
                   set_handler=self._handle_limit_clear)
        t.register(":CALCulate#:LIMit:OFFSet:AMPLitude",
                   handler=self._handle_limit_offset_ampl)
        t.register(":CALCulate#:LIMit:OFFSet:STIMulus",
                   handler=self._handle_limit_offset_stim)

        # Trace math / memory (SNA5000: CALC:MATH)
        t.register(":CALCulate#:MATH:FUNCtion",
                   handler=self._handle_math_func)
        t.register(":CALCulate#:MATH:MEMorize",
                   set_handler=self._handle_math_memorize)
        t.register(":CALCulate#:MATH:STATistics:STATe",
                   handler=self._handle_math_stats_state)
        t.register(":CALCulate#:MATH:STATistics:DATA",
                   query_handler=self._handle_math_stats_data)

        # Display — scale (with :SCALe level)
        t.register(":DISPlay:WINDow#:TRACe#:Y:SCALe:RLEVel",
                   handler=self._handle_disp_rlevel)
        t.register(":DISPlay:WINDow#:TRACe#:Y:SCALe:PDIVision",
                   handler=self._handle_disp_pdiv)
        t.register(":DISPlay:WINDow#:TRACe#:Y:SCALe:RPOSition",
                   handler=self._handle_disp_rpos)
        t.register(":DISPlay:WINDow#:TRACe#:Y:SCALe:AUTO",
                   set_handler=self._handle_disp_auto_scale)
        t.register(":DISPlay:MAXimize", set_handler=self._handle_noop_sna)

        # Trigger
        t.register(":INITiate#:CONTinuous", set_handler=self._handle_init_cont)
        t.register(":TRIGger:SCOPe", set_handler=self._handle_trig_scope)
        t.register(":TRIGger:SEQuence:SOURce",
                   handler=self._handle_trig_src_query)
        t.register(":TRIGger:SEQuence:SING", set_handler=self._handle_trig_sing)
        t.register(":TRIGger:SEQuence:IMMediate",
                   set_handler=self._handle_trig_sing)
        t.register(":TRIGger:POINt", handler=self._handle_trig_point)
        t.register(":TRIGger:EXTernal:SLOPe",
                   handler=self._handle_noop_sna_query)
        t.register(":TRIGger:OUTPut:STATe",
                   handler=self._handle_noop_sna_query)

        # Display — channel/trace management
        t.register(":DISPlay:CHANnel:LIST", query_handler=self._handle_chan_list)
        t.register(":DISPlay:TRACe:LIST", query_handler=self._handle_trace_list)
        t.register(":DISPlay:CHANnel#:TRACe:LIST",
                   query_handler=self._handle_chan_trace_list)
        t.register(":DISPlay:ADD:FUNCtion:EXECute",
                   set_handler=self._handle_add_function)
        t.register(":DISPlay:CHANnel#:ACTivate",
                   set_handler=self._handle_chan_activate)
        t.register(":DISPlay:TRACe#:ACTivate",
                   set_handler=self._handle_trace_activate)

        # Balanced topology
        t.register(":CALCulate#:DTOPology", handler=self._handle_dtopology)

        # Scale (via CALCulate subsystem, SNA5000 alternate path)
        t.register(":CALCulate#:SCALe:DIVision",
                   handler=self._handle_disp_pdiv)
        t.register(":CALCulate#:SCALe:RLEVel",
                   handler=self._handle_disp_rlevel)
        t.register(":CALCulate#:SCALe:RPOSition",
                   handler=self._handle_disp_rpos)
        t.register(":CALCulate#:SCALe:AUTO",
                   set_handler=self._handle_disp_auto_scale)

        # Correction coefficients (with :DATA level)
        t.register(":SENSe#:CORRection:COEFficient:DATA",
                   handler=self._handle_corr_coef_data)
        t.register(":SENSe#:CORRection:COEFficient:SAVE",
                   set_handler=self._handle_corr_coef_save)
        t.register(":SENSe#:CORRection:COEFficient:METHod:RESPonse:OPEN",
                   set_handler=self._handle_corr_meth)
        t.register(":SENSe#:CORRection:COEFficient:METHod:RESPonse:SHORt",
                   set_handler=self._handle_corr_meth)
        t.register(":SENSe#:CORRection:COEFficient:METHod:RESPonse:THRU",
                   set_handler=self._handle_corr_meth)
        t.register(":SENSe#:CORRection:COEFficient:METHod:ERESponse",
                   set_handler=self._handle_corr_meth)
        t.register(":SENSe#:CORRection:COEFficient:METHod:SOLT#",
                   set_handler=self._handle_corr_meth)

        # Segment sweep (bulk + total points/time)
        t.register(":SENSe#:SEGMent:DATA", handler=self._handle_seg_data)
        t.register(":SENSe#:SEGMent:SWEep:POINts",
                   query_handler=self._handle_seg_swp_points_total)
        t.register(":SENSe#:SEGMent:SWEep:TIME",
                   query_handler=self._handle_seg_swp_time_total)

    def _handle_noop_sna(self, cmd: ParsedCommand) -> str | None:
        return None

    def _handle_noop_sna_query(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            return "0"
        return None

    def _parse_seg_data(self, cmd: ParsedCommand) -> tuple[int, float]:
        """Parse segment sweep payload and return total points/time."""
        state = self._ch(cmd)
        if not state.segment_data:
            return state.num_points, state.sweep_time
        parts = [part.strip() for part in state.segment_data.split(",")]
        if len(parts) < 3:
            return state.num_points, state.sweep_time
        try:
            seg_count = int(float(parts[1]))
        except ValueError:
            return state.num_points, state.sweep_time
        cursor = 2
        if len(parts) >= 3 + seg_count * 5:
            cursor = 3
        total_points = 0
        total_time = 0.0
        for _ in range(seg_count):
            if cursor + 4 >= len(parts):
                break
            try:
                total_points += int(float(parts[cursor + 2]))
                total_time += float(parts[cursor + 4]) / 1000.0
            except ValueError:
                return state.num_points, state.sweep_time
            cursor += 5
        if total_points == 0:
            return state.num_points, state.sweep_time
        return total_points, total_time

    def _handle_seg_swp_points_total(self, cmd: ParsedCommand) -> str:
        total_points, _ = self._parse_seg_data(cmd)
        return str(total_points)

    def _handle_seg_swp_time_total(self, cmd: ParsedCommand) -> str:
        _, total_time = self._parse_seg_data(cmd)
        return str(total_time)


# =====================================================================
# ENA-style abbreviated commands (E5071B, CMT, R&S, Anritsu share these)
# =====================================================================

class ENACommandsMixin:
    """ENA-style abbreviated SCPI paths shared by multiple vendors."""

    def _register_ena(self) -> None:
        t = self._tree

        # Sweep type
        t.register(":SENSe#:SWEep:TYPE", handler=self._handle_swp_type)

        # IFBW direct (no :RES)
        t.register(":SENSe#:BANDwidth", handler=self._handle_ifbw)

        # Averaging direct (no :STATe) + count + clear
        t.register(":SENSe#:AVERage", handler=self._handle_avg_state)
        t.register(":SENSe#:AVERage:COUNt", handler=self._handle_avg_count)
        t.register(":SENSe#:AVERage:CLEar", set_handler=self._handle_avg_clear)

        # Smoothing direct (no :STATe)
        t.register(":CALCulate#:SMOothing", handler=self._handle_smooth_state)
        t.register(":CALCulate#:SMOothing:APERture",
                   handler=self._handle_smooth_aperture)

        # Trace parameter (indexed)
        t.register(":CALCulate#:PARameter#:DEFine",
                   handler=self._handle_calc_par_def)
        t.register(":CALCulate#:PARameter#:SELect",
                   set_handler=self._handle_calc_par_sel)
        t.register(":CALCulate#:PARameter:COUNt",
                   handler=self._handle_par_count)

        # Data paths (CALC level)
        t.register(":CALCulate#:DATA:SDAT",
                   query_handler=self._handle_calc_sel_sdata)
        t.register(":CALCulate#:DATA:FDAT",
                   query_handler=self._handle_calc_sel_fdata)
        t.register(":CALCulate#:DATA:FMEM",
                   query_handler=self._handle_data_fmem)
        t.register(":CALCulate#:DATA:SMEM",
                   query_handler=self._handle_data_smem)

        # Trace format (CALC level)
        t.register(":CALCulate#:FORMat", handler=self._handle_calc_sel_fmt)

        # Electrical delay (E5071B: CALC:CORR:EDEL:TIME)
        t.register(":CALCulate#:CORRection:EDELay:TIME",
                   handler=self._handle_elec_delay)
        t.register(":CALCulate#:CORRection:OFFSet:PHASe",
                   handler=self._handle_phase_offset)

        # Markers (E5071B: CALC:MARK{1-10})
        t.register(":CALCulate#:MARKer#:STATe",
                   handler=self._handle_marker_state)
        t.register(":CALCulate#:MARKer#:ACTivate",
                   set_handler=self._handle_marker_activate)
        t.register(":CALCulate#:MARKer#:X", handler=self._handle_marker_x)
        t.register(":CALCulate#:MARKer#:Y",
                   query_handler=self._handle_marker_y)
        t.register(":CALCulate#:MARKer#:DISCrete",
                   handler=self._handle_marker_discrete)
        t.register(":CALCulate#:MARKer#:COUPle",
                   handler=self._handle_marker_coupling)
        t.register(":CALCulate#:MARKer#:REFerence",
                   handler=self._handle_marker_ref_state)
        t.register(":CALCulate#:MARKer#:SET",
                   set_handler=self._handle_marker_set)
        t.register(":CALCulate#:MARKer#:FUNCtion:TYPE",
                   handler=self._handle_marker_func_type)
        t.register(":CALCulate#:MARKer#:FUNCtion:EXECute",
                   set_handler=self._handle_marker_func_exec)
        t.register(":CALCulate#:MARKer#:FUNCtion:TARGet",
                   handler=self._handle_marker_func_target)
        t.register(":CALCulate#:MARKer#:FUNCtion:TTRansition",
                   handler=self._handle_marker_func_ttrans)
        t.register(":CALCulate#:MARKer#:FUNCtion:TRACking",
                   handler=self._handle_marker_func_tracking)
        t.register(":CALCulate#:MARKer#:FUNCtion:DOMain",
                   handler=self._handle_marker_func_domain_state)
        t.register(":CALCulate#:MARKer#:FUNCtion:DOMain:STARt",
                   handler=self._handle_marker_func_domain_start)
        t.register(":CALCulate#:MARKer#:FUNCtion:DOMain:STOP",
                   handler=self._handle_marker_func_domain_stop)
        t.register(":CALCulate#:MARKer#:BWIDth",
                   handler=self._handle_marker_bw_state)
        t.register(":CALCulate#:MARKer#:BWIDth:DATA",
                   query_handler=self._handle_marker_bw_data)
        t.register(":CALCulate#:MARKer#:BWIDth:THReshold",
                   handler=self._handle_marker_bw_threshold)

        # Limit lines (E5071B: CALC:LIM)
        t.register(":CALCulate#:LIMit", handler=self._handle_limit_state)
        t.register(":CALCulate#:LIMit:DISPlay",
                   handler=self._handle_limit_display)
        t.register(":CALCulate#:LIMit:FAIL",
                   query_handler=self._handle_limit_fail)
        t.register(":CALCulate#:LIMit:DATA", handler=self._handle_limit_data)
        t.register(":CALCulate#:LIMit:OFFSet:AMPLitude",
                   handler=self._handle_limit_offset_ampl)
        t.register(":CALCulate#:LIMit:OFFSet:STIMulus",
                   handler=self._handle_limit_offset_stim)

        # Trace math / memory (E5071B: CALC:MATH)
        t.register(":CALCulate#:MATH:FUNCtion",
                   handler=self._handle_math_func)
        t.register(":CALCulate#:MATH:MEMorize",
                   set_handler=self._handle_math_memorize)
        t.register(":CALCulate#:MATH:STATistics:STATe",
                   handler=self._handle_math_stats_state)
        t.register(":CALCulate#:MATH:STATistics:DATA",
                   query_handler=self._handle_math_stats_data)

        # Trigger (ENA-style)
        t.register(":TRIGger:SOURce", handler=self._handle_trig_src_query)
        t.register(":TRIGger:SING", set_handler=self._handle_trig_sing)
        t.register(":TRIGger:SCOPe", set_handler=self._handle_trig_scope)
        t.register(":TRIGger:POINt", handler=self._handle_trig_point)
        t.register(":INITiate#:CONTinuous", set_handler=self._handle_init_cont)
        t.register(":INITiate#:IMMediate", set_handler=self._handle_init_imm)

        # Channel activation
        t.register(":DISPlay:WINDow#:ACT",
                   set_handler=self._handle_chan_activate)
        t.register(":DISPlay:WINDow#:Y:AUTO",
                   set_handler=self._handle_disp_auto_scale)

        # Data format
        t.register(":FORMat:DATA", handler=self._handle_form_data)

        # Port count and channel count
        t.register(":SERVice:PORT:COUNt",
                   query_handler=self._handle_serv_port_count)
        t.register(":SERVice:CHANnel:COUNt",
                   query_handler=self._handle_serv_chan_count)
        t.register(":SERVice:CHANnel:TRACe:COUNt",
                   query_handler=self._handle_serv_trace_count)
        t.register(":SERVice:CHANnel:ACTive",
                   query_handler=self._handle_serv_active_ch)
        t.register(":SERVice:CHANnel:TRACe:ACTive",
                   query_handler=self._handle_serv_active_trace)
        t.register(":SERVice:SWEep:FREQuency:MAXimum",
                   query_handler=self._handle_serv_freq_max)
        t.register(":SERVice:SWEep:FREQuency:MINimum",
                   query_handler=self._handle_serv_freq_min)
        t.register(":SERVice:SWEep:POINts",
                   query_handler=self._handle_serv_swp_points_max)

        # Display scale (without :SCALe)
        t.register(":DISPlay:WINDow#:TRACe#:Y:RLEVel",
                   handler=self._handle_disp_rlevel)
        t.register(":DISPlay:WINDow#:TRACe#:Y:PDIVision",
                   handler=self._handle_disp_pdiv)
        t.register(":DISPlay:WINDow#:TRACe#:Y:RPOSition",
                   handler=self._handle_disp_rpos)

        # Correction (without :DATA level)
        t.register(":SENSe#:CORRection:COEFficient",
                   handler=self._handle_corr_coef_data)
        t.register(":SENSe#:CORRection:COEFficient:SAVE",
                   set_handler=self._handle_corr_coef_save)
        t.register(":SENSe#:CORRection:COEFficient:METHod:OPEN",
                   set_handler=self._handle_corr_meth)
        t.register(":SENSe#:CORRection:COEFficient:METHod:SHORt",
                   set_handler=self._handle_corr_meth)
        t.register(":SENSe#:CORRection:COEFficient:METHod:THRU",
                   set_handler=self._handle_corr_meth)
        t.register(":SENSe#:CORRection:COEFficient:METHod:ERESponse",
                   set_handler=self._handle_corr_meth)
        t.register(":SENSe#:CORRection:COEFficient:METHod:SOLT#",
                   set_handler=self._handle_corr_meth)

        # Port extension (E5071B: SENS:CORR:EXT)
        t.register(":SENSe#:CORRection:EXTension",
                   handler=self._handle_port_ext_state)

        # Segment sweep (bulk)
        t.register(":SENSe#:SEGMent:DATA", handler=self._handle_seg_data)
        t.register(":SENSe#:SEGMent:COUNt",
                   query_handler=self._handle_seg_count_ena)

        # Frequency list
        t.register(":SENSe#:FREQuency:DATA", query_handler=self._handle_freq_data)

    # -- ENA-specific handlers --

    def _handle_par_count(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            ch = cmd.channel
            count = sum(1 for ts in self._traces.values() if ts.channel == ch)
            return str(max(count, 1))
        return None

    def _handle_form_data(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            return "ASC"
        return None

    def _handle_serv_port_count(self, cmd: ParsedCommand) -> str:
        return str(self._num_ports)

    def _handle_serv_chan_count(self, cmd: ParsedCommand) -> str:
        return str(len(self._channels))

    def _handle_serv_trace_count(self, cmd: ParsedCommand) -> str:
        return str(len(self._traces))

    def _handle_serv_active_ch(self, cmd: ParsedCommand) -> str:
        return str(self._active_channel)

    def _handle_serv_active_trace(self, cmd: ParsedCommand) -> str:
        return str(self._active_trace)

    def _handle_serv_freq_max(self, cmd: ParsedCommand) -> str:
        return "8500000000"

    def _handle_serv_freq_min(self, cmd: ParsedCommand) -> str:
        return "300000"

    def _handle_serv_swp_points_max(self, cmd: ParsedCommand) -> str:
        return "1601"

    def _handle_seg_count_ena(self, cmd: ParsedCommand) -> str:
        state = self._ch(cmd)
        if not state.segment_data:
            return "0"
        parts = state.segment_data.split(",")
        if len(parts) >= 2:
            return parts[1]
        return "0"


# =====================================================================
# E5080 measurement-number model
# =====================================================================

@dataclass
class SegmentState:
    start_freq: float = 1e6
    stop_freq: float = 6e9
    num_points: int = 201
    if_bandwidth: float = 1000.0


class E5080CommandsMixin:
    """Keysight E5080-specific SCPI paths (CALC:MEAS model, CSET, etc.)."""

    def _register_e5080(self) -> None:
        t = self._tree

        # Measurement model
        t.register(":CALCulate#:MEASure#:DEFine",
                   handler=self._handle_meas_def)
        t.register(":CALCulate#:MEASure#:PARameter",
                   handler=self._handle_meas_par)
        t.register(":CALCulate#:MEASure#:DATA:SDATA",
                   query_handler=self._handle_calc_sel_sdata)
        t.register(":CALCulate#:MEASure#:DATA:FDATA",
                   query_handler=self._handle_calc_sel_fdata)
        t.register(":CALCulate#:MEASure#:X",
                   query_handler=self._handle_freq_data)
        t.register(":CALCulate#:MEASure#:FORMat",
                   handler=self._handle_meas_form)
        t.register(":CALCulate#:MEASure#:SMOothing",
                   handler=self._handle_smooth_state)
        t.register(":CALCulate#:MEASure#:SMOothing:APERture",
                   handler=self._handle_smooth_aperture)

        # Sweep mode
        t.register(":SENSe#:SWEep:MODE", handler=self._handle_swp_mode)

        # System queries
        t.register(":SYSTem:CAPability:HARDware:PORT:INTernal:COUNt",
                   query_handler=self._handle_syst_port_count)
        t.register(":SYSTem:CHANnel:CATalog",
                   query_handler=self._handle_chan_catalog)

        # Display (measurement-indexed)
        t.register(":DISPlay:WINDow#:STATe",
                   set_handler=self._handle_noop)
        t.register(":DISPlay:MEASure#:FEED",
                   set_handler=self._handle_noop)
        t.register(":DISPlay:MEASure#:Y:RLEVel",
                   handler=self._handle_disp_rlevel)
        t.register(":DISPlay:MEASure#:Y:PDIVision",
                   handler=self._handle_disp_pdiv)
        t.register(":DISPlay:MEASure#:Y:RPOSition",
                   handler=self._handle_disp_rpos)

        # Cal Set
        t.register(":SENSe#:CORRection:CSET:CREate",
                   set_handler=self._handle_noop)
        t.register(":SENSe#:CORRection:CSET:CREate:DEFault",
                   set_handler=self._handle_noop)
        t.register(":SENSe#:CORRection:CSET:DATA",
                   handler=self._handle_corr_coef_data)
        t.register(":SENSe#:CORRection:CSET:SAVE",
                   set_handler=self._handle_noop)
        t.register(":SENSe#:CORRection:CSET:ACTivate",
                   handler=self._handle_cset_activate)

        # Per-segment commands
        t.register(":SENSe#:SEGMent:DELete:ALL",
                   set_handler=self._handle_seg_del_all)
        t.register(":SENSe#:SEGMent:COUNt",
                   query_handler=self._handle_seg_count)
        t.register(":SENSe#:SEGMent#:ADD",
                   set_handler=self._handle_seg_add)
        t.register(":SENSe#:SEGMent#:FREQuency:STARt",
                   handler=self._handle_seg_freq_start)
        t.register(":SENSe#:SEGMent#:FREQuency:STOP",
                   handler=self._handle_seg_freq_stop)
        t.register(":SENSe#:SEGMent#:SWEep:POINts",
                   handler=self._handle_seg_swp_points)
        t.register(":SENSe#:SEGMent#:BWIDth",
                   handler=self._handle_seg_bwid)
        t.register(":SENSe#:SEGMent:BWIDth:CONTrol",
                   set_handler=self._handle_noop)
        t.register(":SENSe#:SEGMent:POWer:CONTrol",
                   set_handler=self._handle_noop)

    # -- E5080-specific handlers --

    def _handle_noop(self, cmd: ParsedCommand) -> str | None:
        return None

    def _handle_meas_def(self, cmd: ParsedCommand) -> str | None:
        return self._handle_calc_par_def(cmd)

    def _handle_meas_par(self, cmd: ParsedCommand) -> str | None:
        return self._handle_calc_par_def(cmd)

    def _handle_meas_form(self, cmd: ParsedCommand) -> str | None:
        tr = cmd.trace
        if tr not in self._traces:
            from vnasim.models.common import TraceState
            self._traces[tr] = TraceState(channel=cmd.channel)
        if cmd.is_query:
            return self._traces[tr].format
        self._traces[tr].format = cmd.arguments.strip()
        return None

    def _handle_swp_mode(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            return "SING"
        return None

    def _handle_syst_port_count(self, cmd: ParsedCommand) -> str:
        return str(self._num_ports)

    def _handle_chan_catalog(self, cmd: ParsedCommand) -> str:
        chs = ",".join(str(ch) for ch in sorted(self._channels))
        return f'"{chs}"'

    def _handle_cset_activate(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            return '"vna_frontend_ch1"'
        return None

    # Segment handlers need per-model segment storage
    _segments: dict

    def _handle_seg_del_all(self, cmd: ParsedCommand) -> str | None:
        self._segments[cmd.channel] = []
        return None

    def _handle_seg_count(self, cmd: ParsedCommand) -> str:
        return str(len(self._segments.get(cmd.channel, [])))

    def _handle_seg_add(self, cmd: ParsedCommand) -> str | None:
        ch = cmd.channel
        if ch not in self._segments:
            self._segments[ch] = []
        self._segments[ch].append(SegmentState())
        return None

    def _get_segment(self, cmd: ParsedCommand) -> SegmentState:
        ch = cmd.channel
        s = cmd.trace - 1
        segs = self._segments.get(ch, [])
        while len(segs) <= s:
            segs.append(SegmentState())
        return segs[s]

    def _handle_seg_freq_start(self, cmd: ParsedCommand) -> str | None:
        seg = self._get_segment(cmd)
        if cmd.is_query:
            return str(seg.start_freq)
        seg.start_freq = float(cmd.arguments)
        return None

    def _handle_seg_freq_stop(self, cmd: ParsedCommand) -> str | None:
        seg = self._get_segment(cmd)
        if cmd.is_query:
            return str(seg.stop_freq)
        seg.stop_freq = float(cmd.arguments)
        return None

    def _handle_seg_swp_points(self, cmd: ParsedCommand) -> str | None:
        seg = self._get_segment(cmd)
        if cmd.is_query:
            return str(seg.num_points)
        seg.num_points = int(float(cmd.arguments))
        return None

    def _handle_seg_bwid(self, cmd: ParsedCommand) -> str | None:
        seg = self._get_segment(cmd)
        if cmd.is_query:
            return str(seg.if_bandwidth)
        seg.if_bandwidth = float(cmd.arguments)
        return None


# =====================================================================
# R&S ZNB/ZNA/ZVA commands
# =====================================================================

class RSZNBCommandsMixin:
    """R&S-specific SCPI paths (named traces, CORR:CDAT, etc.)."""

    def _register_rs(self) -> None:
        t = self._tree

        # Named traces
        t.register(":CALCulate#:PARameter:SDEFine",
                   set_handler=self._handle_par_sdef)
        t.register(":CALCulate#:PARameter:SELect",
                   set_handler=self._handle_par_sel_named)
        t.register(":CALCulate#:PARameter:CATalog",
                   query_handler=self._handle_par_cat)
        t.register(":CALCulate#:PARameter:DELete",
                   set_handler=self._handle_noop_rs)

        # Data with argument after ?
        t.register(":CALCulate#:DATA",
                   query_handler=self._handle_calc_data_with_arg)
        t.register(":CALCulate#:DATA:STIMulus",
                   query_handler=self._handle_freq_data)
        t.register(":CALCulate#:DATA:CALL",
                   query_handler=self._handle_calc_sel_sdata)

        # Port count
        t.register(":INSTrument:NPORt:COUNt",
                   query_handler=self._handle_inst_nport_count)
        t.register(":INSTrument:PORT:COUNt",
                   query_handler=self._handle_inst_nport_count)

        # Channel catalog
        t.register(":CONFigure:CHANnel:CATalog",
                   query_handler=self._handle_conf_chan_cat)

        # Display
        t.register(":DISPlay:WINDow#:STATe",
                   handler=self._handle_disp_wind_stat)
        t.register(":DISPlay:WINDow#:TRACe#:FEED",
                   set_handler=self._handle_noop_rs)

        # Cal coefficients (named terms)
        t.register(":SENSe#:CORRection:CDATa",
                   handler=self._handle_corr_coef_data)

        # Cal method
        t.register(":SENSe#:CORRection:COLLect:METHod:DEFine",
                   set_handler=self._handle_noop_rs)
        t.register(":SENSe#:CORRection:COLLect:SAVE:SELect:DEFault",
                   set_handler=self._handle_noop_rs)

    # -- R&S-specific handlers --

    def _handle_noop_rs(self, cmd: ParsedCommand) -> str | None:
        return None

    def _handle_par_sdef(self, cmd: ParsedCommand) -> str | None:
        args = cmd.arguments.strip()
        parts = [p.strip().strip("'\"") for p in args.split(",")]
        param = parts[1] if len(parts) > 1 else parts[0]
        tr_state = self._tr(cmd)
        tr_state.parameter = param.upper()
        tr_state.channel = cmd.channel
        return None

    def _handle_par_sel_named(self, cmd: ParsedCommand) -> str | None:
        self._active_channel = cmd.channel
        return None

    def _handle_par_cat(self, cmd: ParsedCommand) -> str:
        ch = cmd.channel
        for tr, ts in self._traces.items():
            if ts.channel == ch:
                return f"'VNALab','{ts.parameter}'"
        return "'VNALab','S11'"

    def _handle_calc_data_with_arg(self, cmd: ParsedCommand) -> str | None:
        arg = cmd.arguments.strip().upper()
        if arg == "SDAT":
            return self._handle_calc_sel_sdata(cmd)
        elif arg == "FDAT":
            return self._handle_calc_sel_fdata(cmd)
        return None

    def _handle_inst_nport_count(self, cmd: ParsedCommand) -> str:
        return str(self._num_ports)

    def _handle_conf_chan_cat(self, cmd: ParsedCommand) -> str:
        """Response: ``'1,Ch1,2,Ch2'`` (number,name pairs)."""
        parts = []
        for ch in sorted(self._channels):
            parts.extend([str(ch), f"Ch{ch}"])
        return "'" + ",".join(parts) + "'"

    def _handle_disp_wind_stat(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            return "ON"
        return None


# =====================================================================
# Copper Mountain commands
# =====================================================================

class CopperMountainCommandsMixin:
    """Copper Mountain-specific SCPI paths (:BWID, :TRAC:SMOO, :XAX)."""

    def _register_cmt(self) -> None:
        t = self._tree

        # IFBW via :BWID
        t.register(":SENSe#:BWIDth", handler=self._handle_ifbw)

        # Smoothing via :TRAC:SMOO
        t.register(":CALCulate#:TRACe:SMOothing",
                   handler=self._handle_smooth_state)
        t.register(":CALCulate#:TRACe:SMOothing:APERture",
                   handler=self._handle_smooth_aperture)

        # Frequency list via :DATA:XAX
        t.register(":CALCulate#:DATA:XAXis",
                   query_handler=self._handle_freq_data)


# =====================================================================
# Anritsu ShockLine commands
# =====================================================================

class AnritsuCommandsMixin:
    """Anritsu ShockLine-specific SCPI paths."""

    def _register_anritsu(self) -> None:
        t = self._tree

        # Sweep type — TYPe (3-char short form)
        t.register(":SENSe#:SWEep:TYPe", handler=self._handle_swp_type)

        # Hold/trigger
        t.register(":SENSe#:HOLD:FUNCtion",
                   handler=self._handle_hold_func)

        # Cal coefficients (single-argument, no port numbers)
        t.register(":SENSe#:CORRection:COEFficient",
                   handler=self._handle_corr_coef_anritsu)

        # Cal collection type
        t.register(":SENSe#:CORRection:COLLect:TYPe",
                   query_handler=self._handle_corr_coll_type)

        # Per-port cal method commands
        t.register(":SENSe#:CORRection:COEFficient:PORT12:FULL2",
                   set_handler=self._handle_noop_anritsu)
        t.register(":SENSe#:CORRection:COEFficient:PORT#:FULL1",
                   set_handler=self._handle_noop_anritsu)
        t.register(":SENSe#:CORRection:COEFficient:PORT#:RESP1",
                   set_handler=self._handle_noop_anritsu)
        t.register(":SENSe#:CORRection:COEFficient:PORT12:1P2PF",
                   set_handler=self._handle_noop_anritsu)
        t.register(":SENSe#:CORRection:COEFficient:PORT12:TFRF",
                   set_handler=self._handle_noop_anritsu)

    # -- Anritsu-specific handlers --

    def _handle_noop_anritsu(self, cmd: ParsedCommand) -> str | None:
        return None

    def _handle_hold_func(self, cmd: ParsedCommand) -> str | None:
        if cmd.is_query:
            return "HOLD"
        return None

    def _handle_corr_coef_anritsu(self, cmd: ParsedCommand) -> str | None:
        state = self._ch(cmd)
        if cmd.is_query:
            n = state.num_points
            term = cmd.arguments.strip().upper()
            if term in state.cal_coefficients:
                return self._format_complex(state.cal_coefficients[term])
            if "ET" in term or "ERFT" in term:
                return self._format_complex(self._ideal_coef("ER", n))
            return self._format_complex(self._ideal_coef("ED", n))
        args = cmd.arguments.strip()
        parts = args.split(",")
        if parts:
            key = parts[0].strip().upper()
            vals = [float(x) for x in parts[1:]]
            data = np.array(vals[0::2]) + 1j * np.array(vals[1::2])
            state.cal_coefficients[key] = data
        return None

    def _handle_corr_coll_type(self, cmd: ParsedCommand) -> str:
        return "NONE"
