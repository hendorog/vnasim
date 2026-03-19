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


TRANSLATORS: dict[str, type] = {
    "sna5000": SNA5000Translator,
}
