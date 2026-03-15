"""Integration tests — start server, connect via TCP, send SCPI commands."""

import asyncio
import logging
import socket


from vnasim.models.sna5000 import SNA5000Model
from vnasim.server import start_instrument


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def _run_test(coro):
    """Start a test instrument and run *coro(port, model)*."""
    model = SNA5000Model(
        num_ports=2,
        idn="Siglent Technologies,SNA5012A,TEST,1.0",
    )
    port = _find_free_port()
    server = await start_instrument(model, port=port, name="test", host="127.0.0.1")
    try:
        await coro(port, model)
    finally:
        server.close()
        await server.wait_closed()


async def _query(reader, writer, cmd: str) -> str:
    writer.write((cmd + "\n").encode("ascii"))
    await writer.drain()
    data = await asyncio.wait_for(reader.readline(), timeout=5.0)
    return data.decode("ascii").strip()


async def _send(writer, cmd: str) -> None:
    writer.write((cmd + "\n").encode("ascii"))
    await writer.drain()


def test_idn_query():
    async def body(port, model):
        r, w = await asyncio.open_connection("127.0.0.1", port)
        try:
            resp = await _query(r, w, "*IDN?")
            assert "Siglent" in resp
            assert "SNA5012A" in resp
        finally:
            w.close()
            await w.wait_closed()
    asyncio.run(_run_test(body))


def test_opc_query():
    async def body(port, model):
        r, w = await asyncio.open_connection("127.0.0.1", port)
        try:
            assert await _query(r, w, "*OPC?") == "1"
        finally:
            w.close()
            await w.wait_closed()
    asyncio.run(_run_test(body))


def test_set_and_query_frequency():
    async def body(port, model):
        r, w = await asyncio.open_connection("127.0.0.1", port)
        try:
            await _send(w, ":SENSe1:FREQuency:STARt 1000000.0")
            await _send(w, ":SENSe1:FREQuency:STOP 6000000000.0")
            assert await _query(r, w, "*OPC?") == "1"
            assert await _query(r, w, ":SENSe1:FREQuency:STARt?") == "1000000.0"
            assert await _query(r, w, ":SENSe1:FREQuency:STOP?") == "6000000000.0"
        finally:
            w.close()
            await w.wait_closed()
    asyncio.run(_run_test(body))


def test_full_sweep_sequence():
    async def body(port, model):
        r, w = await asyncio.open_connection("127.0.0.1", port)
        try:
            # Configure
            await _send(w, ":SENSe1:FREQuency:STARt 1e6")
            await _send(w, ":SENSe1:FREQuency:STOP 6e9")
            await _send(w, ":SENSe1:SWEep:POINts 11")
            assert await _query(r, w, "*OPC?") == "1"

            # Set measurement
            await _send(w, ":CALCulate1:PARameter1:DEFine S21")
            await _send(w, ":CALCulate1:PARameter1:SELect")

            # Trigger sequence
            await _send(w, ":DISPlay:TRACe1:ACTivate")
            await _send(w, ":INITiate1:CONTinuous ON")
            await _send(w, ":TRIGger:SCOPe ACTive")
            await _send(w, ":TRIGger:SEQuence:SOURce BUS")
            await _send(w, ":TRIGger:SEQuence:SING")
            assert await _query(r, w, "*OPC?") == "1"

            # Read corrected data
            raw = await _query(r, w, ":SENSe1:DATA:CORRdata? S21")
            vals = raw.split(",")
            assert len(vals) == 22  # 11 points * 2 (re,im)

            # Read frequency list
            freq_raw = await _query(r, w, ":SENSe1:FREQuency:DATA?")
            freqs = freq_raw.split(",")
            assert len(freqs) == 11

            # Restore trigger
            await _send(w, ":TRIGger:SEQuence:SOURce INTERNAL")
        finally:
            w.close()
            await w.wait_closed()
    asyncio.run(_run_test(body))


def test_multiple_clients_share_state():
    async def body(port, model):
        r1, w1 = await asyncio.open_connection("127.0.0.1", port)
        r2, w2 = await asyncio.open_connection("127.0.0.1", port)
        try:
            await _send(w1, ":SENSe1:FREQuency:STARt 500e6")
            assert await _query(r1, w1, "*OPC?") == "1"
            start = await _query(r2, w2, ":SENSe1:FREQuency:STARt?")
            assert start == "500000000.0"
        finally:
            w1.close()
            await w1.wait_closed()
            w2.close()
            await w2.wait_closed()
    asyncio.run(_run_test(body))


def test_write_command_no_response():
    async def body(port, model):
        r, w = await asyncio.open_connection("127.0.0.1", port)
        try:
            await _send(w, ":SENSe1:FREQuency:STARt 1e6")
            assert await _query(r, w, "*OPC?") == "1"
        finally:
            w.close()
            await w.wait_closed()
    asyncio.run(_run_test(body))


def test_unhandled_command_logged_with_context(caplog):
    """An unrecognised SCPI command logs a WARNING with preceding context."""
    async def body(port, model):
        r, w = await asyncio.open_connection("127.0.0.1", port)
        try:
            # Send a few valid commands to build up history
            await _send(w, ":SENSe1:FREQuency:STARt 1e6")
            await _send(w, ":SENSe1:FREQuency:STOP 6e9")
            assert await _query(r, w, "*OPC?") == "1"

            # Send an unrecognised command (write — no TCP response)
            await _send(w, ":SYSTem:ERRor:FAKE 42")

            # Send a following command so "after" context is captured
            assert await _query(r, w, "*OPC?") == "1"
        finally:
            w.close()
            await w.wait_closed()

    with caplog.at_level(logging.WARNING, logger="vnasim.server"):
        asyncio.run(_run_test(body))

    # Check the WARNING log was emitted
    warning_text = "\n".join(
        rec.message for rec in caplog.records if rec.levelno >= logging.WARNING
    )
    assert "UNHANDLED SCPI" in warning_text
    assert ":SYSTem:ERRor:FAKE 42" in warning_text
    # Preceding context should include the valid commands
    assert "FREQ" in warning_text.upper() or "OPC" in warning_text.upper()
    # After-context line should mention the OPC query that followed
    assert "context after" in warning_text
