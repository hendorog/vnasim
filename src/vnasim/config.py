"""YAML configuration loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class InstrumentConfig:
    name: str
    model: str
    port: int
    num_ports: int = 2
    idn: str = ""


def load_config(path: str | Path) -> list[InstrumentConfig]:
    """Load instrument definitions from a YAML file."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    instruments = []
    for entry in raw.get("instruments", []):
        instruments.append(InstrumentConfig(
            name=entry["name"],
            model=entry["model"],
            port=entry["port"],
            num_ports=entry.get("num_ports", 2),
            idn=entry.get("idn", ""),
        ))
    return instruments
