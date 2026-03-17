"""Asyncio TCP server — one listening port per simulated instrument."""

from __future__ import annotations

import asyncio
import logging
from collections import deque

from vnasim.models.base import VNAModel
from vnasim.scpi.types import Unhandled

logger = logging.getLogger(__name__)

# How many commands before/after an unhandled command to include in the log.
_CONTEXT_BEFORE = 5
_CONTEXT_AFTER = 5


async def _handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    model: VNAModel,
    name: str,
) -> None:
    """Handle one TCP client connection."""
    peer = writer.get_extra_info("peername")
    logger.info("[%s] Client connected: %s", name, peer)

    # Rolling window of recent commands for context logging.
    # Each entry is a string like  "<<< :SENS1:FREQ:STAR 1e6"
    # or  "<<< *OPC?  >>> 1".
    history: deque[str] = deque(maxlen=_CONTEXT_BEFORE)

    # After an unhandled command we keep logging the next N commands
    # so the developer can see what the client does next.
    after_remaining = 0
    after_tag = ""  # the unhandled command string (for the log prefix)

    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            line = data.decode("ascii", errors="replace").strip()
            if not line:
                continue

            logger.debug("[%s] <<< %s", name, line)
            # run_in_executor so proxy models can do blocking backend I/O
            # without stalling the event loop for other clients.
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, model.handle, line)

            if isinstance(result, Unhandled):
                # ---- Log the unhandled command with surrounding context ----
                before = list(history)
                parts = [
                    f"[{name}] UNHANDLED SCPI: {result.raw!r}  "
                    f"({result.reason})",
                ]
                if before:
                    parts.append("  preceding commands:")
                    for entry in before:
                        parts.append(f"    {entry}")
                parts.append(
                    f"  (next {_CONTEXT_AFTER} commands will be logged "
                    f"for additional context)"
                )
                logger.warning("\n".join(parts))

                history.append(f"<<< {line}  [UNHANDLED: {result.reason}]")
                after_remaining = _CONTEXT_AFTER
                after_tag = result.raw
            elif result is not None:
                # Query with a response.
                entry = f"<<< {line}  >>> {result[:80]}"
                history.append(entry)
                logger.debug("[%s] >>> %s", name, result[:120])
                writer.write((result + "\n").encode("ascii"))
                await writer.drain()

                if after_remaining > 0:
                    logger.warning(
                        "[%s] context after %r (+%d): %s",
                        name, after_tag,
                        _CONTEXT_AFTER - after_remaining + 1, entry,
                    )
                    after_remaining -= 1
            else:
                # Handled write command, no response.
                entry = f"<<< {line}"
                history.append(entry)

                if after_remaining > 0:
                    logger.warning(
                        "[%s] context after %r (+%d): %s",
                        name, after_tag,
                        _CONTEXT_AFTER - after_remaining + 1, entry,
                    )
                    after_remaining -= 1

    except (ConnectionResetError, asyncio.IncompleteReadError):
        pass
    except Exception:
        logger.exception("[%s] Error handling client %s", name, peer)
    finally:
        logger.info("[%s] Client disconnected: %s", name, peer)
        writer.close()
        await writer.wait_closed()


async def start_instrument(
    model: VNAModel,
    port: int,
    name: str,
    host: str = "0.0.0.0",
) -> asyncio.Server:
    """Start a TCP server for one simulated instrument."""

    async def on_connect(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
    ) -> None:
        asyncio.create_task(_handle_client(reader, writer, model, name))

    server = await asyncio.start_server(on_connect, host, port)
    logger.info("[%s] Listening on %s:%d", name, host, port)
    return server


async def run_all(
    instruments: list[tuple[VNAModel, int, str]],
    host: str = "0.0.0.0",
) -> None:
    """Start all instrument servers and run forever.

    *instruments* is a list of ``(model, port, name)`` tuples.
    """
    servers = []
    for model, port, name in instruments:
        srv = await start_instrument(model, port, name, host)
        servers.append(srv)

    try:
        await asyncio.Event().wait()  # Run forever
    finally:
        for srv in servers:
            srv.close()
        for srv in servers:
            await srv.wait_closed()
