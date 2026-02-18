from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import json
import logging
import threading
from typing import Callable

LOGGER = logging.getLogger(__name__)

if hasattr(ctypes, "windll"):
    kernel32 = ctypes.windll.kernel32
else:
    kernel32 = None

INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
PIPE_ACCESS_DUPLEX = 0x00000003
PIPE_TYPE_BYTE = 0x00000000
PIPE_READMODE_BYTE = 0x00000000
PIPE_WAIT = 0x00000000
PIPE_UNLIMITED_INSTANCES = 255
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3


class NamedPipeServer:
    def __init__(self, pipe_name: str, request_handler: Callable[[dict], dict]) -> None:
        self.pipe_name = pipe_name
        self.request_handler = request_handler
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if kernel32 is None:
            raise RuntimeError("Named pipe is only supported on Windows")
        self._thread = threading.Thread(target=self._serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _serve_forever(self) -> None:
        LOGGER.info("Named Pipe待受開始: %s", self.pipe_name)
        while not self._stop_event.is_set():
            h_pipe = kernel32.CreateNamedPipeW(
                ctypes.c_wchar_p(self.pipe_name),
                PIPE_ACCESS_DUPLEX,
                PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
                PIPE_UNLIMITED_INSTANCES,
                65536,
                65536,
                0,
                None,
            )
            if h_pipe == INVALID_HANDLE_VALUE:
                LOGGER.error("CreateNamedPipe失敗")
                continue

            connected = kernel32.ConnectNamedPipe(h_pipe, None)
            if connected == 0:
                err = kernel32.GetLastError()
                if err != 535:  # ERROR_PIPE_CONNECTED
                    kernel32.CloseHandle(h_pipe)
                    continue

            threading.Thread(target=self._handle_client, args=(h_pipe,), daemon=True).start()

    def _handle_client(self, h_pipe: int) -> None:
        try:
            buffer = b""
            while True:
                chunk, ok = _read_file(h_pipe)
                if not ok:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        request = json.loads(line.decode("utf-8"))
                        response = self.request_handler(request)
                    except Exception as exc:
                        response = {
                            "ok": False,
                            "error": {"code": "INTERNAL", "message": str(exc)},
                        }
                    _write_file(h_pipe, (json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
        finally:
            kernel32.DisconnectNamedPipe(h_pipe)
            kernel32.CloseHandle(h_pipe)


def _read_file(handle: int, size: int = 4096) -> tuple[bytes, bool]:
    buf = ctypes.create_string_buffer(size)
    read = wintypes.DWORD(0)
    ok = kernel32.ReadFile(handle, buf, size, ctypes.byref(read), None)
    if ok == 0:
        return b"", False
    return buf.raw[: read.value], True


def _write_file(handle: int, payload: bytes) -> None:
    written = wintypes.DWORD(0)
    kernel32.WriteFile(handle, payload, len(payload), ctypes.byref(written), None)


def send_request(pipe_name: str, request: dict) -> dict:
    if kernel32 is None:
        raise RuntimeError("Named pipe client is only supported on Windows")

    h_pipe = kernel32.CreateFileW(
        ctypes.c_wchar_p(pipe_name),
        GENERIC_READ | GENERIC_WRITE,
        0,
        None,
        OPEN_EXISTING,
        0,
        None,
    )
    if h_pipe == INVALID_HANDLE_VALUE:
        raise RuntimeError("could not connect to pipe")

    try:
        _write_file(h_pipe, (json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"))
        buffer = b""
        while True:
            chunk, ok = _read_file(h_pipe)
            if not ok:
                raise RuntimeError("pipe closed before response")
            buffer += chunk
            if b"\n" in buffer:
                line, _ = buffer.split(b"\n", 1)
                return json.loads(line.decode("utf-8"))
    finally:
        kernel32.CloseHandle(h_pipe)
