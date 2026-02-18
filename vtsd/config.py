from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ReconnectBackoff:
    min: int = 300
    max: int = 5000


@dataclass(slots=True)
class VtsdConfig:
    pipe_name: str = r"\\.\pipe\vtsd"
    vts_host: str = "localhost"
    vts_port: int = 8001
    default_call_timeout_ms: int = 5000
    max_queue_size: int = 1024
    auto_token_request: bool = False
    token_path: str = r"%APPDATA%\vtsd\token.txt"
    reconnect_backoff_ms: ReconnectBackoff = field(default_factory=ReconnectBackoff)
    plugin_name: str = "vtsd"
    plugin_developer: str = "vtsd"

    @property
    def ws_url(self) -> str:
        return f"ws://{self.vts_host}:{self.vts_port}"


def _default_config_paths() -> list[Path]:
    cwd = Path.cwd() / "vtsd.json"
    appdata = Path(os.path.expandvars(r"%APPDATA%")) / "vtsd" / "vtsd.json"
    return [cwd, appdata]


def load_config(path: str | None = None) -> VtsdConfig:
    if path:
        candidates = [Path(path)]
    else:
        candidates = _default_config_paths()

    raw: dict[str, Any] = {}
    for p in candidates:
        if p.exists():
            raw = json.loads(p.read_text(encoding="utf-8"))
            break

    backoff = raw.get("reconnect_backoff_ms", {})
    cfg = VtsdConfig(
        pipe_name=raw.get("pipe_name", VtsdConfig.pipe_name),
        vts_host=raw.get("vts_host", VtsdConfig.vts_host),
        vts_port=raw.get("vts_port", VtsdConfig.vts_port),
        default_call_timeout_ms=raw.get("default_call_timeout_ms", VtsdConfig.default_call_timeout_ms),
        max_queue_size=raw.get("max_queue_size", VtsdConfig.max_queue_size),
        auto_token_request=raw.get("auto_token_request", VtsdConfig.auto_token_request),
        token_path=raw.get("token_path", VtsdConfig.token_path),
        reconnect_backoff_ms=ReconnectBackoff(
            min=backoff.get("min", ReconnectBackoff.min),
            max=backoff.get("max", ReconnectBackoff.max),
        ),
        plugin_name=raw.get("plugin_name", VtsdConfig.plugin_name),
        plugin_developer=raw.get("plugin_developer", VtsdConfig.plugin_developer),
    )
    cfg.token_path = os.path.expandvars(cfg.token_path)
    return cfg
