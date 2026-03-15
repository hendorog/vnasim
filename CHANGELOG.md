# Changelog

## 0.1.0 — 2026-03-15

Initial release.

### Core
- Asyncio TCP server with one listening port per simulated instrument
- Tree-based SCPI parser with IEEE 488.2 short-form matching and numeric suffix extraction
- Per-channel/trace state machine (frequency, sweep, IFBW, power, averaging, smoothing, calibration, display scale)
- Synthetic S-parameter data generation (3-port duplexer model with bandpass, isolation, passivity-based reflection)
- Formatted data output (MLOGarithmic, PHASe, SMITH, POLar, etc.)
- Calibration coefficient storage/retrieval with ideal defaults
- Multi-client support with shared instrument state
- YAML-based configuration for instrument definitions
- Unhandled command logging with before/after context to `vnasim_unhandled.log`

### Instrument Models
- **Siglent SNA5000A** (`sna5000`) — full command set (~50 SCPI commands), balanced topology, wave quantities, segment sweep, multi-channel/trace management
- **Keysight E5071B/C** (`e5071b`) — ENA-style abbreviated commands, `:CALC:DATA:SDAT?`/`:FDAT?`, `:CALC:FORM`, `:TRIG:SOUR`/`:TRIG:SING`, `:SERV:PORT:COUN?`, `:FORM:DATA`
- **Keysight E5080A/B** (`e5080`) — measurement-number model (`CALC:MEAS{m}:DEF`), `SWE:MODE SING` + `INIT:IMM` trigger, Cal Set stubs (`CSET:DATA`/`SAVE`/`ACT`), per-segment configuration, `SYST:CAP:HARD:PORT:INT:COUN?`, `SYST:CHAN:CAT?`
- **Copper Mountain S2VNA/S4VNA** (`copper_mountain`) — `:BWID` for IFBW, `:CALC:TRAC:SMOO` for smoothing, `:CALC:DATA:XAX?` for frequency list
- **R&S ZNB/ZNA/ZVA** (`rs_znb`) — named traces (`PAR:SDEF`/`SEL`/`CAT?`), `DATA? SDAT`/`FDAT` argument-after-query, `DATA:STIM?`, `INST:NPORT:COUN?`, `CORR:CDAT` for calibration, `INIT:IMM` trigger
- **Anritsu ShockLine MS46xxx** (`anritsu_shockline`) — `:SWE:TYPe` (3-char short form), `:HOLD:FUNC` trigger model, `FSEGM` segment type, single-argument cal coefficients (`ED1`/`EP1S`/etc.), per-port cal method commands

