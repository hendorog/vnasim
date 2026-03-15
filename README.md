# vnasim — Multi-VNA SCPI Communications Simulator

A TCP-based simulator that emulates multiple VNA instruments over the network. Any SCPI client connects to the simulator exactly as it would to real hardware and receives realistic responses — no physical instruments required.

## Quick Start

```bash
pip install -e ".[dev]"
python -m vnasim config.yaml
```

The simulator starts one TCP listener per instrument defined in `config.yaml`. Connect using a VISA resource string:

```
TCPIP::localhost::5025::SOCKET
```

with the appropriate driver type selected.

## Supported Instruments

| Model | `config.yaml` type | Default Port |
|-------|-------------------|-------------|
| Siglent SNA5000A 2-port | `sna5000` | 5025 |
| Siglent SNA5000A 4-port | `sna5000` | 5026 |
| Keysight E5071B 2-port | `e5071b` | 5027 |
| Keysight E5071C 4-port | `e5071b` | 5028 |
| Keysight E5080B 2-port | `e5080` | 5029 |
| Keysight E5080B 4-port | `e5080` | 5030 |
| Copper Mountain S2VNA | `copper_mountain` | 5031 |
| R&S ZNB8 4-port | `rs_znb` | 5032 |
| Anritsu MS46522B | `anritsu_shockline` | 5033 |

## Configuration

Edit `config.yaml` to choose which instruments to simulate:

```yaml
instruments:
  - name: "My SNA5012A"
    model: sna5000
    port: 5025
    num_ports: 2
    idn: "Siglent Technologies,SNA5012A,SNA5XXXX00001,2.3.1.3.1r1"
```

Each entry needs:
- **model** — one of the types listed above
- **port** — TCP port to listen on
- **num_ports** — number of VNA ports (2 or 4)
- **idn** — the `*IDN?` response string (controls auto-detection by the client application)

## How It Works

```
SCPI Client  -->  TCP socket  -->  SCPI Parser  -->  VNA Model  -->  Synthetic Data
                  (per instrument)   (tree-based,     (state machine,   (duplexer
                                      short-form       per-channel)      S-params)
                                      matching)
```

- **SCPI Parser** — tree-based command router with IEEE 488.2 short-form matching. `SENS`, `SENSE`, `SENSe` all match. Handles numeric suffixes for channel/trace indices.
- **VNA Models** — each model maintains per-channel state (frequency, points, IFBW, power, averaging, calibration coefficients, etc.) and registers its SCPI command tree. Models inherit from each other where command sets overlap.
- **Synthetic Data** — generates a realistic 3-port duplexer response (bandpass transmission, passivity-based reflection, TX-RX isolation).

## Unhandled Command Logging

When the simulator receives a command it doesn't recognise, it logs a `WARNING` with the preceding 5 commands and the following 5 commands for context. These are written to both the console and `vnasim_unhandled.log` (truncated on each restart).

This makes it straightforward to identify and implement missing commands.

## Tests

```bash
python -m pytest tests/ -v
```

## Adding a New VNA Model

1. Create `src/vnasim/models/my_vna.py` subclassing an existing model (or `VNAModel`)
2. Override `_build_tree()` to register the instrument's SCPI command paths
3. Add the model to `MODEL_REGISTRY` in `models/__init__.py`
4. Add an entry to `config.yaml`

The SCPI parser, TCP server, and synthetic data generation are fully reusable across models.

## Architecture

```
src/vnasim/
    __main__.py            CLI entry point
    server.py              asyncio TCP server (one port per instrument)
    config.py              YAML config loader
    scpi/
        parser.py          Tree-based SCPI command router
        types.py           ParsedCommand and Unhandled types
    models/
        base.py            Abstract VNAModel interface
        sna5000.py         Siglent SNA5000A (base model, ~50 commands)
        keysight_ena.py    Keysight E5071B/C (extends SNA5000)
        keysight_e5080.py  Keysight E5080A/B (extends E5071B)
        copper_mountain.py Copper Mountain S2VNA/S4VNA (extends E5071B)
        rs_znb.py          R&S ZNB/ZNA/ZVA (extends E5071B)
        anritsu_shockline.py Anritsu MS46xxx (extends E5071B)
    data/
        synthetic.py       S-parameter data generation
```

Model inheritance: `SNA5000 --> E5071B --> E5080, CopperMountain, RSZNB, AnritsuShockLine`
