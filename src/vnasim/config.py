"""YAML configuration loader."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class BackendConfig:
    host: str
    port: int
    dialect: str  # e.g. "sna5000"


@dataclass
class InstrumentConfig:
    name: str
    model: str
    port: int
    num_ports: int = 2
    idn: str = ""
    mode: str = "synthetic"  # "synthetic" or "proxy"
    backend: BackendConfig | None = None


def load_config(path: str | Path) -> list[InstrumentConfig]:
    """Load instrument definitions from a YAML file."""
    with open(path) as f:
        raw = yaml.safe_load(f)

    instruments = []
    for entry in raw.get("instruments", []):
        backend = None
        if "backend" in entry:
            b = entry["backend"]
            backend = BackendConfig(
                host=b["host"],
                port=b["port"],
                dialect=b["dialect"],
            )
        instruments.append(InstrumentConfig(
            name=entry["name"],
            model=entry["model"],
            port=entry["port"],
            num_ports=entry.get("num_ports", 2),
            idn=entry.get("idn", ""),
            mode=entry.get("mode", "synthetic"),
            backend=backend,
        ))
    return instruments
