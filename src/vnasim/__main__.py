"""Entry point: python -m vnasim [config.yaml]"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from vnasim.config import InstrumentConfig, load_config
from vnasim.models import MODEL_REGISTRY
from vnasim.server import run_all

# Proxy model composition: frontend dialect → mixin sets
_PROXY_MIXINS: dict[str, tuple] = {}


def _create_proxy(cfg: InstrumentConfig, backends: list) -> object:
    """Create a proxy model from config, connecting to the real backend."""
    from vnasim.backend.client import BackendClient
    from vnasim.backend.translator import TRANSLATORS
    from vnasim.models.proxy import ProxyVNAModel
    from vnasim.models import mixins as mx

    if cfg.backend is None:
        raise ValueError(f"Proxy instrument {cfg.name!r} has no backend config")

    translator_cls = TRANSLATORS.get(cfg.backend.dialect)
    if translator_cls is None:
        raise ValueError(f"Unknown backend dialect: {cfg.backend.dialect!r}")

    # Map frontend model name to the mixins it needs
    mixin_map: dict[str, tuple] = {
        "sna5000": (mx.SiglentCommandsMixin,),
        "e5071b": (mx.ENACommandsMixin,),
        "e5080": (mx.ENACommandsMixin, mx.E5080CommandsMixin),
        "copper_mountain": (mx.ENACommandsMixin, mx.CopperMountainCommandsMixin),
        "rs_znb": (mx.ENACommandsMixin, mx.RSZNBCommandsMixin),
        "anritsu_shockline": (mx.ENACommandsMixin, mx.AnritsuCommandsMixin),
    }
    frontend_mixins = mixin_map.get(cfg.model)
    if frontend_mixins is None:
        raise ValueError(f"No proxy mixin mapping for model: {cfg.model!r}")

    # Build the _build_tree method name list from the mixins
    register_methods = ["_register_core"]
    for mixin in frontend_mixins:
        # Each mixin has a _register_xxx method — find it
        for name in dir(mixin):
            if name.startswith("_register_") and name != "_register_core":
                register_methods.append(name)

    # Dynamically compose the proxy class
    bases = (ProxyVNAModel,) + frontend_mixins

    def _build_tree(self):
        for method_name in register_methods:
            getattr(self, method_name)()

    cls = type(
        f"Proxy_{cfg.model}",
        bases,
        {"_build_tree": _build_tree},
    )

    # Share a single backend connection per host:port
    backend_key = (cfg.backend.host, cfg.backend.port)
    backend = None
    for existing in backends:
        if (existing._host, existing._port) == backend_key:
            backend = existing
            break
    if backend is None:
        backend = BackendClient(cfg.backend.host, cfg.backend.port)
        backend.connect()
        backends.append(backend)

    # E5080 needs _segments dict
    model = object.__new__(cls)
    if hasattr(mx.E5080CommandsMixin, '_segments'):
        model._segments = {}
    cls.__init__(
        model,
        num_ports=cfg.num_ports,
        idn=cfg.idn,
        backend=backend,
        translator=translator_cls(),
    )
    return model


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
    backends = []  # track for shutdown
    for cfg in configs:
        if cfg.mode == "proxy":
            model = _create_proxy(cfg, backends)
        else:
            model_cls = MODEL_REGISTRY.get(cfg.model)
            if model_cls is None:
                print(f"Unknown model type: {cfg.model!r}", file=sys.stderr)
                sys.exit(1)
            model = model_cls(num_ports=cfg.num_ports, idn=cfg.idn)
        instruments.append((model, cfg.port, cfg.name))
        logging.getLogger(__name__).info(
            "Configured %s (%s%s) on port %d",
            cfg.name, cfg.model,
            f" → {cfg.backend.dialect}@{cfg.backend.host}:{cfg.backend.port}"
            if cfg.backend else "",
            cfg.port,
        )

    try:
        asyncio.run(run_all(instruments))
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Shutting down.")
    finally:
        for b in backends:
            try:
                b.disconnect()
            except Exception:
                pass


if __name__ == "__main__":
    main()
