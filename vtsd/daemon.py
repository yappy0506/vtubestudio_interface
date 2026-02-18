from __future__ import annotations

import asyncio
import logging
from typing import Any

from .config import VtsdConfig
from .ipc_pipe import NamedPipeServer
from .protocol import ProtocolError, err, ok_call, ok_cast, validate_request
from .vts_client import VtsClient

LOGGER = logging.getLogger(__name__)


class VtsDaemon:
    def __init__(self, config: VtsdConfig) -> None:
        self.config = config
        self.loop: asyncio.AbstractEventLoop | None = None
        self.vts = VtsClient(config)
        self.pipe_server = NamedPipeServer(config.pipe_name, self._handle_request_sync)

    async def run(self) -> None:
        LOGGER.info("vtsd 起動")
        self.loop = asyncio.get_running_loop()
        await self.vts.start()
        self.pipe_server.start()
        await asyncio.Event().wait()

    def _handle_request_sync(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.loop is None:
            return err(request.get("clientRequestId"), "INTERNAL", "event loop is not ready")
        future = asyncio.run_coroutine_threadsafe(self._handle_request(request), self.loop)
        return future.result()

    async def _handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        client_request_id = request.get("clientRequestId")
        try:
            req = validate_request(request)
        except ProtocolError as exc:
            return err(client_request_id, "IPC_BAD_REQUEST", str(exc))
        except Exception as exc:
            return err(client_request_id, "INTERNAL", str(exc))

        op = req["op"]
        message_type = req["messageType"]
        data = req["data"]
        LOGGER.info("IPC受理 op=%s messageType=%s clientRequestId=%s", op, message_type, client_request_id)

        if op == "cast":
            accepted, reason = await self.vts.cast(message_type, data)
            return ok_cast(client_request_id, accepted, reason)

        timeout = req.get("timeoutMs") or self.config.default_call_timeout_ms
        response_mode = req.get("responseMode", "data")
        ok, result_or_error = await self.vts.call(message_type, data, timeout, response_mode)
        if ok:
            return ok_call(client_request_id, result_or_error)
        return err(
            client_request_id,
            result_or_error.get("code", "INTERNAL"),
            result_or_error.get("message", "unknown error"),
            result_or_error.get("detail"),
        )
