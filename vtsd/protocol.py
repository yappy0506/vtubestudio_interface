from __future__ import annotations

from typing import Any


ALLOWED_OPS = {"cast", "call"}
ALLOWED_RESPONSE_MODES = {"raw", "data"}


class ProtocolError(ValueError):
    pass


def validate_request(payload: dict[str, Any]) -> dict[str, Any]:
    op = payload.get("op")
    if op not in ALLOWED_OPS:
        raise ProtocolError("op must be cast/call")

    message_type = payload.get("messageType")
    if not isinstance(message_type, str) or not message_type:
        raise ProtocolError("messageType is required")

    normalized: dict[str, Any] = {
        "op": op,
        "messageType": message_type,
        "data": payload.get("data"),
        "clientRequestId": payload.get("clientRequestId"),
    }

    if op == "call":
        timeout = payload.get("timeoutMs")
        if timeout is not None and (not isinstance(timeout, int) or timeout <= 0):
            raise ProtocolError("timeoutMs must be positive integer")
        normalized["timeoutMs"] = timeout

        mode = payload.get("responseMode", "data")
        if mode not in ALLOWED_RESPONSE_MODES:
            raise ProtocolError("responseMode must be raw/data")
        normalized["responseMode"] = mode

    return normalized


def ok_cast(client_request_id: str | None, accepted: bool, reason: str | None = None) -> dict[str, Any]:
    resp: dict[str, Any] = {"ok": True, "clientRequestId": client_request_id, "accepted": accepted}
    if reason:
        resp["reason"] = reason
    return resp


def ok_call(client_request_id: str | None, result: Any) -> dict[str, Any]:
    return {"ok": True, "clientRequestId": client_request_id, "result": result}


def err(client_request_id: str | None, code: str, message: str, detail: Any | None = None) -> dict[str, Any]:
    e: dict[str, Any] = {"code": code, "message": message}
    if detail is not None:
        e["detail"] = detail
    return {"ok": False, "clientRequestId": client_request_id, "error": e}
