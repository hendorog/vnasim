"""Synchronous TCP client for communicating with a real backend VNA."""

from __future__ import annotations

import logging
import socket
import threading

logger = logging.getLogger(__name__)


class BackendClient:
    """Plain TCP socket client with newline-terminated protocol.

    Thread-safe — all socket operations are serialised with a lock so
    multiple frontend clients sharing one backend cannot interleave.
    """

    def __init__(self, host: str, port: int, timeout: float = 30.0) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._socket: socket.socket | None = None
        self._recv_buf: bytes = b""
        self._lock = threading.Lock()

    def connect(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self._timeout)
        sock.connect((self._host, self._port))
        self._socket = sock
        self._recv_buf = b""

        # Some instruments send a welcome banner on connect — drain it.
        import select
        while select.select([sock], [], [], 0.5)[0]:
            chunk = sock.recv(4096)
            if not chunk:
                break
            banner = chunk.decode("ascii", errors="replace").strip()
            if banner:
                logger.info("Backend banner: %s", banner)

        logger.info("Backend connected to %s:%d", self._host, self._port)

    def disconnect(self) -> None:
        sock = self._socket
        self._socket = None
        self._recv_buf = b""
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    @property
    def is_connected(self) -> bool:
        return self._socket is not None

    def write(self, command: str) -> None:
        with self._lock:
            if self._socket is None:
                raise ConnectionError("Backend not connected.")
            self._socket.sendall((command + "\n").encode("ascii"))

    def query(self, command: str) -> str:
        with self._lock:
            if self._socket is None:
                raise ConnectionError("Backend not connected.")
            self._socket.sendall((command + "\n").encode("ascii"))
            return self._read_line()

    def _read_line(self) -> str:
        while b"\n" not in self._recv_buf:
            chunk = self._socket.recv(65536)
            if not chunk:
                raise ConnectionError("Backend connection closed.")
            self._recv_buf += chunk
        line, self._recv_buf = self._recv_buf.split(b"\n", 1)
        # Strip null bytes and other control characters that some
        # instruments inject at the start of responses.
        text = line.decode("ascii", errors="replace")
        return text.strip().strip("\x00")
