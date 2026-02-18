from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import websockets

from .config import VtsdConfig

LOGGER = logging.getLogger(__name__)

NON_AUTH_GATED_TYPES = {"APIStateRequest", "AuthenticationTokenRequest", "AuthenticationRequest"}


class VtsDisconnectedError(Exception):
    pass


@dataclass(slots=True)
class QueueItem:
    payload: dict[str, Any]


class VtsClient:
    def __init__(self, config: VtsdConfig) -> None:
        self.config = config
        self.connection_state = "DISCONNECTED"
        self.auth_state = "UNKNOWN"
        self.ws: websockets.WebSocketClientProtocol | None = None
        self.send_queue: asyncio.Queue[QueueItem] = asyncio.Queue(maxsize=config.max_queue_size)
        self.pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._worker_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._worker_task = asyncio.create_task(self._connection_loop())

    async def stop(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(Exception):
                await self._worker_task

    def is_connected(self) -> bool:
        return self.connection_state == "CONNECTED" and self.ws is not None

    def is_authenticated(self) -> bool:
        return self.auth_state == "AUTHENTICATED"

    async def cast(self, message_type: str, data: Any | None) -> tuple[bool, str | None]:
        if not self.is_connected():
            return False, "VTS_NOT_CONNECTED"
        if message_type not in NON_AUTH_GATED_TYPES and not self.is_authenticated():
            return False, "AUTH_REQUIRED"
        payload = self._build_payload(message_type, data)
        if self.send_queue.full():
            return False, "QUEUE_FULL"
        await self.send_queue.put(QueueItem(payload=payload))
        return True, None

    async def call(self, message_type: str, data: Any | None, timeout_ms: int, response_mode: str) -> tuple[bool, Any]:
        if not self.is_connected():
            return False, {"code": "VTS_NOT_CONNECTED", "message": "VTS websocket is disconnected"}
        if message_type not in NON_AUTH_GATED_TYPES and not self.is_authenticated():
            return False, {"code": "AUTH_REQUIRED", "message": "Session is not authenticated"}

        payload = self._build_payload(message_type, data)
        request_id = payload["requestID"]
        fut: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self.pending[request_id] = fut

        if self.send_queue.full():
            self.pending.pop(request_id, None)
            return False, {"code": "INTERNAL", "message": "Queue full", "detail": {"reason": "QUEUE_FULL"}}

        await self.send_queue.put(QueueItem(payload=payload))

        try:
            raw = await asyncio.wait_for(fut, timeout=timeout_ms / 1000)
        except asyncio.TimeoutError:
            self.pending.pop(request_id, None)
            return False, {"code": "VTS_TIMEOUT", "message": "Timeout waiting VTS response"}
        except VtsDisconnectedError:
            return False, {"code": "VTS_DISCONNECTED", "message": "Disconnected while waiting response"}

        if raw.get("messageType") == "APIError":
            return False, {"code": "VTS_API_ERROR", "message": "VTS returned APIError", "detail": raw}

        if response_mode == "data":
            return True, raw.get("data")
        return True, raw

    async def _connection_loop(self) -> None:
        delay_ms = self.config.reconnect_backoff_ms.min
        while True:
            self.connection_state = "CONNECTING"
            self.auth_state = "UNKNOWN"
            try:
                LOGGER.info("VTS接続を試行: %s", self.config.ws_url)
                async with websockets.connect(self.config.ws_url) as ws:
                    self.ws = ws
                    self.connection_state = "CONNECTED"
                    LOGGER.info("VTS接続成功")
                    delay_ms = self.config.reconnect_backoff_ms.min
                    await self._establish_auth()
                    await asyncio.gather(self._sender_loop(), self._receiver_loop())
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                LOGGER.warning("VTS接続/処理エラー: %s", exc)
            finally:
                self.connection_state = "DISCONNECTED"
                self.auth_state = "UNKNOWN"
                self.ws = None
                self._fail_all_pending()

            await asyncio.sleep(delay_ms / 1000)
            delay_ms = min(delay_ms * 2, self.config.reconnect_backoff_ms.max)

    async def _sender_loop(self) -> None:
        while self.ws:
            item = await self.send_queue.get()
            await self.ws.send(json.dumps(item.payload, ensure_ascii=False))
            LOGGER.debug("VTS送信: requestID=%s messageType=%s", item.payload.get("requestID"), item.payload.get("messageType"))

    async def _receiver_loop(self) -> None:
        assert self.ws is not None
        async for message in self.ws:
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                LOGGER.warning("VTSから不正JSON")
                continue
            request_id = payload.get("requestID")
            if request_id and request_id in self.pending:
                fut = self.pending.pop(request_id)
                if not fut.done():
                    fut.set_result(payload)
            else:
                LOGGER.debug("非対応レスポンス: %s", payload.get("messageType"))

    async def _establish_auth(self) -> None:
        self.auth_state = "UNAUTHENTICATED"
        ok, state = await self.call("APIStateRequest", {}, self.config.default_call_timeout_ms, "raw")
        if ok and state.get("data", {}).get("currentSessionAuthenticated"):
            self.auth_state = "AUTHENTICATED"
            LOGGER.info("既存セッションは認証済み")
            return

        token = self._read_token()
        if token:
            ok, _resp = await self.call(
                "AuthenticationRequest",
                {
                    "pluginName": self.config.plugin_name,
                    "pluginDeveloper": self.config.plugin_developer,
                    "authenticationToken": token,
                },
                self.config.default_call_timeout_ms,
                "raw",
            )
            if ok:
                self.auth_state = "AUTHENTICATED"
                LOGGER.info("セッション認証成功")
                return

        if not token and self.config.auto_token_request:
            ok, token_resp = await self.call(
                "AuthenticationTokenRequest",
                {"pluginName": self.config.plugin_name, "pluginDeveloper": self.config.plugin_developer},
                self.config.default_call_timeout_ms,
                "raw",
            )
            if ok:
                token = token_resp.get("data", {}).get("authenticationToken")
                if token:
                    self._write_token(token)
                    LOGGER.info("認証トークンを保存")
        self.auth_state = "UNAUTHENTICATED"
        LOGGER.info("セッション未認証")

    def _build_payload(self, message_type: str, data: Any | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": str(uuid.uuid4()),
            "messageType": message_type,
        }
        if data is not None:
            payload["data"] = data
        return payload

    def _read_token(self) -> str | None:
        path = Path(self.config.token_path)
        if not path.exists():
            return None
        value = path.read_text(encoding="utf-8").strip()
        return value or None

    def _write_token(self, token: str) -> None:
        path = Path(self.config.token_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(token, encoding="utf-8")

    def _fail_all_pending(self) -> None:
        for fut in self.pending.values():
            if not fut.done():
                fut.set_exception(VtsDisconnectedError())
        self.pending.clear()
