"""Command translators — map semantic VNA operations to backend SCPI.

Each translator knows the SCPI grammar of one backend dialect.
"""

from __future__ import annotations


class SNA5000Translator:
    """Translate semantic VNA operations to Siglent SNA5000 SCPI."""

    # -- Frequency / Sweep --

    def set_freq_start(self, ch: int, value: float) -> str:
        return f":SENSe{ch}:FREQuency:STARt {value}"

    def query_freq_start(self, ch: int) -> str:
        return f":SENSe{ch}:FREQuency:STARt?"

    def set_freq_stop(self, ch: int, value: float) -> str:
        return f":SENSe{ch}:FREQuency:STOP {value}"

    def query_freq_stop(self, ch: int) -> str:
        return f":SENSe{ch}:FREQuency:STOP?"

    def set_freq_cw(self, ch: int, value: float) -> str:
        return f":SENSe{ch}:FREQuency:CW {value}"

    def query_freq_cw(self, ch: int) -> str:
        return f":SENSe{ch}:FREQuency:CW?"

    def query_freq_data(self, ch: int) -> str:
        return f":SENSe{ch}:FREQuency:DATA?"

    def set_swp_points(self, ch: int, value: int) -> str:
        return f":SENSe{ch}:SWEep:POINts {value}"

    def query_swp_points(self, ch: int) -> str:
        return f":SENSe{ch}:SWEep:POINts?"

    def set_swp_type(self, ch: int, value: str) -> str:
        return f":SENSe{ch}:SWEep:TYPE {value}"

    def query_swp_type(self, ch: int) -> str:
        return f":SENSe{ch}:SWEep:TYPE?"

    def query_swp_time(self, ch: int) -> str:
        return f":SENSe{ch}:SWEep:TIME?"

    # -- IFBW --

    def set_ifbw(self, ch: int, value: float) -> str:
        return f":SENSe{ch}:BANDwidth:RESolution {value}"

    def query_ifbw(self, ch: int) -> str:
        return f":SENSe{ch}:BANDwidth:RESolution?"

    # -- Power --

    def set_power(self, ch: int, value: float) -> str:
        return f":SOURce{ch}:POWer {value}"

    def query_power(self, ch: int) -> str:
        return f":SOURce{ch}:POWer?"

    # -- Averaging --

    def set_avg_state(self, ch: int, value: str) -> str:
        return f":SENSe{ch}:AVERage:STATe {value}"

    def query_avg_state(self, ch: int) -> str:
        return f":SENSe{ch}:AVERage:STATe?"

    def query_avg_count(self, ch: int) -> str:
        return f":SENSe{ch}:AVERage:COUNt?"

    # -- Smoothing --

    def set_smooth_state(self, ch: int, value: str) -> str:
        return f":CALCulate{ch}:SMOothing:STATe {value}"

    def query_smooth_state(self, ch: int) -> str:
        return f":CALCulate{ch}:SMOothing:STATe?"

    def set_smooth_aperture(self, ch: int, value: float) -> str:
        return f":CALCulate{ch}:SMOothing:APERture {value}"

    def query_smooth_aperture(self, ch: int) -> str:
        return f":CALCulate{ch}:SMOothing:APERture?"

    # -- Correction --

    def set_corr_state(self, ch: int, value: str) -> str:
        return f":SENSe{ch}:CORRection:STATe {value}"

    def query_corr_state(self, ch: int) -> str:
        return f":SENSe{ch}:CORRection:STATe?"

    def query_corr_coef(self, ch: int, args: str) -> str:
        return f":SENSe{ch}:CORRection:COEFficient:DATA? {args}"

    def set_corr_coef(self, ch: int, args: str) -> str:
        return f":SENSe{ch}:CORRection:COEFficient:DATA {args}"

    # -- Measurement setup --

    def set_measurement(self, ch: int, tr: int, param: str) -> list[str]:
        return [
            f":CALCulate{ch}:PARameter{tr}:DEFine {param}",
            f":CALCulate{ch}:PARameter{tr}:SELect",
        ]

    # -- Trigger --

    def trigger_sweep(self, ch: int, tr: int = 1) -> list[str]:
        return [
            f":DISPlay:TRACe{tr}:ACTivate",
            ":TRIGger:SCOPe ACTive",
            ":TRIGger:SEQuence:SOURce BUS",
            f":INITiate{ch}:IMMediate",
            ":TRIGger:SEQuence:SING",
        ]

    # -- Data queries --

    def query_sdata(self, ch: int, param: str) -> str:
        return f":SENSe{ch}:DATA:CORRdata? {param}"

    def query_raw_data(self, ch: int, param: str) -> str:
        return f":SENSe{ch}:DATA:RAWData? {param}"

    def query_selected_sdata(self, ch: int) -> str:
        return f":CALCulate{ch}:SELected:DATA:SDATa?"

    def query_selected_fdata(self, ch: int) -> str:
        return f":CALCulate{ch}:SELected:DATA:FDATa?"

    def set_trace_format(self, ch: int, fmt: str) -> str:
        return f":CALCulate{ch}:SELected:FORMat {fmt}"

    # -- Segment --

    def set_seg_data(self, ch: int, data: str) -> str:
        return f":SENSe{ch}:SEGMent:DATA {data}"

    def query_seg_data(self, ch: int) -> str:
        return f":SENSe{ch}:SEGMent:DATA?"

    # -- Frequency center/span --

    def set_freq_center(self, ch: int, value: float) -> str:
        return f":SENSe{ch}:FREQuency:CENTer {value}"

    def query_freq_center(self, ch: int) -> str:
        return f":SENSe{ch}:FREQuency:CENTer?"

    def set_freq_span(self, ch: int, value: float) -> str:
        return f":SENSe{ch}:FREQuency:SPAN {value}"

    def query_freq_span(self, ch: int) -> str:
        return f":SENSe{ch}:FREQuency:SPAN?"

    # -- Sweep delay --

    def set_swp_delay(self, ch: int, value: float) -> str:
        return f":SENSe{ch}:SWEep:DELay {value}"

    def query_swp_delay(self, ch: int) -> str:
        return f":SENSe{ch}:SWEep:DELay?"

    # -- Averaging extras --

    def set_avg_count(self, ch: int, value: int) -> str:
        return f":SENSe{ch}:AVERage:COUNt {value}"

    def avg_clear(self, ch: int) -> str:
        return f":CALCulate{ch}:AVERage:CLEar"

    # -- Electrical delay --

    def set_elec_delay(self, ch: int, value: float) -> str:
        return f":CALCulate{ch}:CORRection:EDELay:TIME {value}"

    def query_elec_delay(self, ch: int) -> str:
        return f":CALCulate{ch}:CORRection:EDELay:TIME?"

    # -- Output --

    def set_output(self, value: str) -> str:
        return f":OUTPut {value}"

    def query_output(self) -> str:
        return ":OUTPut?"

    # -- Markers --

    def set_marker_state(self, ch: int, mk: int, value: str) -> str:
        return f":CALCulate{ch}:MARKer{mk}:STATe {value}"

    def query_marker_state(self, ch: int, mk: int) -> str:
        return f":CALCulate{ch}:MARKer{mk}:STATe?"

    def set_marker_activate(self, ch: int, mk: int) -> str:
        return f":CALCulate{ch}:MARKer{mk}:ACTivate"

    def set_marker_x(self, ch: int, mk: int, value: float) -> str:
        return f":CALCulate{ch}:MARKer{mk}:X {value}"

    def query_marker_x(self, ch: int, mk: int) -> str:
        return f":CALCulate{ch}:MARKer{mk}:X?"

    def query_marker_y(self, ch: int, mk: int) -> str:
        return f":CALCulate{ch}:MARKer{mk}:Y?"

    def set_marker_func_type(self, ch: int, mk: int, value: str) -> str:
        return f":CALCulate{ch}:MARKer{mk}:FUNCtion:TYPE {value}"

    def query_marker_func_type(self, ch: int, mk: int) -> str:
        return f":CALCulate{ch}:MARKer{mk}:FUNCtion:TYPE?"

    def marker_func_exec(self, ch: int, mk: int) -> str:
        return f":CALCulate{ch}:MARKer{mk}:FUNCtion:EXECute"

    def set_marker_func_target(self, ch: int, mk: int, value: float) -> str:
        return f":CALCulate{ch}:MARKer{mk}:FUNCtion:TARGet {value}"

    def query_marker_func_target(self, ch: int, mk: int) -> str:
        return f":CALCulate{ch}:MARKer{mk}:FUNCtion:TARGet?"

    def set_marker_func_tracking(self, ch: int, mk: int, value: str) -> str:
        return f":CALCulate{ch}:MARKer{mk}:FUNCtion:TRACking {value}"

    def set_marker_func_domain_state(self, ch: int, mk: int, value: str) -> str:
        return f":CALCulate{ch}:MARKer{mk}:FUNCtion:DOMain:STATe {value}"

    def set_marker_func_domain_start(self, ch: int, mk: int, value: float) -> str:
        return f":CALCulate{ch}:MARKer{mk}:FUNCtion:DOMain:STARt {value}"

    def set_marker_func_domain_stop(self, ch: int, mk: int, value: float) -> str:
        return f":CALCulate{ch}:MARKer{mk}:FUNCtion:DOMain:STOP {value}"

    def set_marker_discrete(self, ch: int, mk: int, value: str) -> str:
        return f":CALCulate{ch}:MARKer{mk}:DISCrete {value}"

    def set_marker_coupling(self, ch: int, value: str) -> str:
        return f":CALCulate{ch}:MARKer:COUPle {value}"

    def set_marker_ref_state(self, ch: int, value: str) -> str:
        return f":CALCulate{ch}:MARKer:REFerence:STATe {value}"

    def marker_set_center(self, ch: int, mk: int) -> str:
        return f":CALCulate{ch}:MARKer{mk}:SET:CENTer"

    def marker_set_start(self, ch: int, mk: int) -> str:
        return f":CALCulate{ch}:MARKer{mk}:SET:STARt"

    def marker_set_stop(self, ch: int, mk: int) -> str:
        return f":CALCulate{ch}:MARKer{mk}:SET:STOP"

    def marker_set_rlevel(self, ch: int, mk: int) -> str:
        return f":CALCulate{ch}:MARKer{mk}:SET:RLEVel"

    def marker_set_delay(self, ch: int, mk: int) -> str:
        return f":CALCulate{ch}:MARKer{mk}:SET:DELay"

    # -- Limit lines --

    def set_limit_state(self, ch: int, value: str) -> str:
        return f":CALCulate{ch}:LIMit:STATe {value}"

    def query_limit_state(self, ch: int) -> str:
        return f":CALCulate{ch}:LIMit:STATe?"

    def set_limit_display(self, ch: int, value: str) -> str:
        return f":CALCulate{ch}:LIMit:DISPlay:STATe {value}"

    def query_limit_fail(self, ch: int) -> str:
        return f":CALCulate{ch}:LIMit:FAIL?"

    def set_limit_data(self, ch: int, data: str) -> str:
        return f":CALCulate{ch}:LIMit:DATA {data}"

    def query_limit_data(self, ch: int) -> str:
        return f":CALCulate{ch}:LIMit:DATA?"

    def limit_clear(self, ch: int) -> str:
        return f":CALCulate{ch}:LIMit:CLEar"

    # -- Math / memory --

    def set_math_func(self, ch: int, value: str) -> str:
        return f":CALCulate{ch}:MATH:FUNCtion {value}"

    def query_math_func(self, ch: int) -> str:
        return f":CALCulate{ch}:MATH:FUNCtion?"

    def math_memorize(self, ch: int) -> str:
        return f":CALCulate{ch}:MATH:MEMorize"

    # -- Power extras --

    def set_port_power(self, ch: int, port: int, value: float) -> str:
        return f":SOURce{ch}:POWer:PORT{port} {value}"

    def query_port_power(self, ch: int, port: int) -> str:
        return f":SOURce{ch}:POWer:PORT{port}?"

    def set_power_coupling(self, ch: int, value: str) -> str:
        return f":SOURce{ch}:POWer:PORT:COUPle {value}"

    def query_power_coupling(self, ch: int) -> str:
        return f":SOURce{ch}:POWer:PORT:COUPle?"

    def set_power_slope(self, ch: int, value: float) -> str:
        return f":SOURce{ch}:POWer:SLOPe {value}"

    def query_power_slope(self, ch: int) -> str:
        return f":SOURce{ch}:POWer:SLOPe?"

    def set_power_slope_state(self, ch: int, value: str) -> str:
        return f":SOURce{ch}:POWer:SLOPe:STATe {value}"

    def query_power_slope_state(self, ch: int) -> str:
        return f":SOURce{ch}:POWer:SLOPe:STATe?"

    def set_power_start(self, ch: int, value: float) -> str:
        return f":SOURce{ch}:POWer:STARt {value}"

    def query_power_start(self, ch: int) -> str:
        return f":SOURce{ch}:POWer:STARt?"

    def set_power_stop(self, ch: int, value: float) -> str:
        return f":SOURce{ch}:POWer:STOP {value}"

    def query_power_stop(self, ch: int) -> str:
        return f":SOURce{ch}:POWer:STOP?"

    # -- Port extension --

    def set_port_ext_state(self, ch: int, value: str) -> str:
        return f":SENSe{ch}:CORRection:EXTension:STATe {value}"

    def query_port_ext_state(self, ch: int) -> str:
        return f":SENSe{ch}:CORRection:EXTension:STATe?"

    def set_port_ext_time(self, ch: int, port: int, value: float) -> str:
        return f":SENSe{ch}:CORRection:EXTension:PORT{port}:TIME {value}"

    def query_port_ext_time(self, ch: int, port: int) -> str:
        return f":SENSe{ch}:CORRection:EXTension:PORT{port}:TIME?"

    def set_velocity_factor(self, ch: int, value: float) -> str:
        return f":SENSe{ch}:CORRection:RVELocity:COAX {value}"

    def query_velocity_factor(self, ch: int) -> str:
        return f":SENSe{ch}:CORRection:RVELocity:COAX?"

    def set_impedance(self, ch: int, value: float) -> str:
        return f":SENSe{ch}:CORRection:IMPedance {value}"

    def query_impedance(self, ch: int) -> str:
        return f":SENSe{ch}:CORRection:IMPedance?"


TRANSLATORS: dict[str, type] = {
    "sna5000": SNA5000Translator,
}
