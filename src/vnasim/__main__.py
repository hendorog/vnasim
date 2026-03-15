"""Entry point: python -m vnasim [config.yaml]"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from vnasim.config import load_config
from vnasim.models import MODEL_REGISTRY
from vnasim.server import run_all


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-5s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    # Log unhandled commands to a file for easy processing
    file_handler = logging.FileHandler("vnasim_unhandled.log", mode="w")
    file_handler.setLevel(logging.WARNING)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(message)s", datefmt="%H:%M:%S",
    ))
    logging.getLogger("vnasim.server").addHandler(file_handler)

    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    if not Path(config_path).exists():
        print(f"Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    configs = load_config(config_path)
    if not configs:
        print("No instruments defined in config.", file=sys.stderr)
        sys.exit(1)

    instruments = []
    for cfg in configs:
        model_cls = MODEL_REGISTRY.get(cfg.model)
        if model_cls is None:
            print(f"Unknown model type: {cfg.model!r}", file=sys.stderr)
            sys.exit(1)
        model = model_cls(num_ports=cfg.num_ports, idn=cfg.idn)
        instruments.append((model, cfg.port, cfg.name))
        logging.getLogger(__name__).info(
            "Configured %s (%s) on port %d", cfg.name, cfg.model, cfg.port,
        )

    try:
        asyncio.run(run_all(instruments))
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Shutting down.")


if __name__ == "__main__":
    main()
