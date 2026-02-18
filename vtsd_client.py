from __future__ import annotations

from typing import Any

from vtsd.ipc_pipe import send_request


class VtsdClient:
    def __init__(self, pipe_name: str = r"\\.\pipe\vtsd") -> None:
        self.pipe_name = pipe_name

    def cast(self, messageType: str, data: Any = None, clientRequestId: str | None = None) -> dict[str, Any]:
        req: dict[str, Any] = {"op": "cast", "messageType": messageType}
        if data is not None:
            req["data"] = data
        if clientRequestId is not None:
            req["clientRequestId"] = clientRequestId
        return send_request(self.pipe_name, req)

    def call(
        self,
        messageType: str,
        data: Any = None,
        timeoutMs: int | None = None,
        responseMode: str = "data",
        clientRequestId: str | None = None,
    ) -> dict[str, Any]:
        req: dict[str, Any] = {"op": "call", "messageType": messageType, "responseMode": responseMode}
        if data is not None:
            req["data"] = data
        if timeoutMs is not None:
            req["timeoutMs"] = timeoutMs
        if clientRequestId is not None:
            req["clientRequestId"] = clientRequestId
        return send_request(self.pipe_name, req)
