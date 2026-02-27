from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from vtsd_client import VtsdClient


DEFAULT_PIPE_NAME = r"\\.\pipe\vtsd-demo"
DEFAULT_VTS_PORT = 8001
DEFAULT_BROADCAST_PORT = 47779


class DemoError(RuntimeError):
    pass


def dump(title: str, payload: Any) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def sleep_seconds(seconds: float, message: str) -> None:
    print(f"[WAIT] {message}: {seconds:.1f}s")
    time.sleep(seconds)


def listen_vts_broadcast(timeout_seconds: float, port: int) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        sock.settimeout(1.0)
        while time.monotonic() < deadline:
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                continue

            try:
                payload = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

            if payload.get("messageType") != "VTubeStudioAPIStateBroadcast":
                continue

            dump(f"VTS Broadcast from {addr[0]}:{addr[1]}", payload)
            return payload
    finally:
        sock.close()

    raise DemoError(
        f"VTSブロードキャストを {timeout_seconds:.1f} 秒待機しましたが受信できませんでした。"
    )


@dataclass
class ManagedVtsd:
    pipe_name: str
    vts_port: int
    token_path: Path
    config_path: Path
    process: subprocess.Popen[Any] | None = None

    @classmethod
    def create(cls, pipe_name: str, vts_port: int) -> "ManagedVtsd":
        temp_dir = Path(tempfile.mkdtemp(prefix="vtsd_demo_"))
        token_path = temp_dir / "token.txt"
        config_path = temp_dir / "vtsd.demo.json"
        managed = cls(pipe_name=pipe_name, vts_port=vts_port, token_path=token_path, config_path=config_path)
        managed._write_config()
        return managed

    def _write_config(self) -> None:
        config = {
            "pipe_name": self.pipe_name,
            "vts_host": "localhost",
            "vts_port": self.vts_port,
            "default_call_timeout_ms": 5000,
            "max_queue_size": 1024,
            "auto_token_request": False,
            "token_path": str(self.token_path),
            "plugin_name": "vtsd-demo",
            "plugin_developer": "vtsd-demo",
        }
        self.config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    def update_port(self, vts_port: int) -> None:
        if self.process and self.process.poll() is None:
            raise DemoError("vtsd起動中はポートを変更できません。")
        self.vts_port = vts_port
        self._write_config()

    def start(self, work_dir: Path) -> None:
        if self.process and self.process.poll() is None:
            return
        self.process = subprocess.Popen(
            [sys.executable, "-m", "vtsd", "--config", str(self.config_path), "--log-level", "INFO"],
            cwd=str(work_dir),
        )

    def stop(self) -> None:
        if not self.process or self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)

    def restart(self, work_dir: Path) -> None:
        self.stop()
        sleep_seconds(1.0, "vtsd再起動待機")
        self.start(work_dir)


def call_api(
    client: VtsdClient,
    message_type: str,
    *,
    data: dict[str, Any] | None = None,
    timeout_ms: int = 5000,
    response_mode: str = "data",
    client_request_id: str | None = None,
) -> dict[str, Any]:
    response = client.call(
        message_type,
        data=data,
        timeoutMs=timeout_ms,
        responseMode=response_mode,
        clientRequestId=client_request_id,
    )
    dump(f"call {message_type}", response)
    return response


def cast_api(
    client: VtsdClient,
    message_type: str,
    *,
    data: dict[str, Any] | None = None,
    client_request_id: str | None = None,
) -> dict[str, Any]:
    response = client.cast(message_type, data=data, clientRequestId=client_request_id)
    dump(f"cast {message_type}", response)
    return response


def wait_until_ready(client: VtsdClient, timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            response = client.call(
                "APIStateRequest",
                timeoutMs=1200,
                responseMode="raw",
                clientRequestId="demo-healthcheck",
            )
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            time.sleep(0.5)
            continue

        if response.get("ok") is True:
            dump("APIStateRequest(healthcheck)", response)
            return response.get("result", {})

        code = response.get("error", {}).get("code")
        if code in {"VTS_NOT_CONNECTED", "VTS_TIMEOUT", "VTS_DISCONNECTED"}:
            last_error = code
            time.sleep(1.0)
            continue

        raise DemoError(f"vtsd準備待ちで予期しないエラー: {response}")

    raise DemoError(f"vtsd準備待ちがタイムアウトしました。last_error={last_error}")


def require_ok(response: dict[str, Any], context: str) -> dict[str, Any]:
    if response.get("ok") is True:
        result = response.get("result")
        if isinstance(result, dict):
            return result
        return {}
    raise DemoError(f"{context} に失敗しました: {response.get('error')}")


def request_token_and_authenticate(
    client: VtsdClient,
    plugin_name: str,
    plugin_developer: str,
    timeout_seconds: float,
) -> str:
    token_response = call_api(
        client,
        "AuthenticationTokenRequest",
        data={"pluginName": plugin_name, "pluginDeveloper": plugin_developer},
        timeout_ms=int(timeout_seconds * 1000),
        response_mode="data",
        client_request_id="demo-auth-token",
    )
    token_data = require_ok(token_response, "AuthenticationTokenRequest")
    token = token_data.get("authenticationToken")
    if not token:
        raise DemoError("AuthenticationTokenRequest の応答に authenticationToken がありません。")

    auth_response = call_api(
        client,
        "AuthenticationRequest",
        data={
            "pluginName": plugin_name,
            "pluginDeveloper": plugin_developer,
            "authenticationToken": token,
        },
        timeout_ms=5000,
        response_mode="data",
        client_request_id="demo-auth-request",
    )
    require_ok(auth_response, "AuthenticationRequest")
    print("[OK] セッション認証が成功しました。")
    return token


def ensure_session_authenticated(
    client: VtsdClient,
    *,
    plugin_name: str,
    plugin_developer: str,
    auth_timeout_seconds: float,
) -> None:
    state_response = call_api(
        client,
        "APIStateRequest",
        timeout_ms=5000,
        response_mode="data",
        client_request_id="demo-auth-check",
    )
    state_data = require_ok(state_response, "APIStateRequest(認証確認)")
    if state_data.get("currentSessionAuthenticated") is True:
        print("[INFO] 既に認証済みセッションです。")
        return
    request_token_and_authenticate(
        client,
        plugin_name=plugin_name,
        plugin_developer=plugin_developer,
        timeout_seconds=auth_timeout_seconds,
    )


def authenticate_with_token(
    client: VtsdClient,
    *,
    token: str,
    plugin_name: str,
    plugin_developer: str,
) -> None:
    auth_response = call_api(
        client,
        "AuthenticationRequest",
        data={
            "pluginName": plugin_name,
            "pluginDeveloper": plugin_developer,
            "authenticationToken": token,
        },
        timeout_ms=5000,
        response_mode="data",
        client_request_id="demo-auth-request-restart",
    )
    require_ok(auth_response, "AuthenticationRequest(再起動後)")


def get_available_models(client: VtsdClient) -> list[dict[str, Any]]:
    response = call_api(
        client,
        "AvailableModelsRequest",
        timeout_ms=5000,
        response_mode="data",
        client_request_id="demo-available-models",
    )
    data = require_ok(response, "AvailableModelsRequest")
    models = data.get("availableModels")
    if not isinstance(models, list):
        return []
    return [m for m in models if isinstance(m, dict)]


def get_current_model_silent(client: VtsdClient, client_request_id: str) -> dict[str, Any]:
    response = client.call(
        "CurrentModelRequest",
        timeoutMs=3000,
        responseMode="data",
        clientRequestId=client_request_id,
    )
    if response.get("ok") is True and isinstance(response.get("result"), dict):
        return response["result"]
    raise DemoError(f"CurrentModelRequest に失敗しました: {response.get('error')}")


def wait_for_model_state(
    client: VtsdClient,
    *,
    expected_loaded: bool,
    expected_model_id: str | None = None,
    timeout_seconds: float = 15.0,
    poll_interval_seconds: float = 0.5,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        current = get_current_model_silent(client, client_request_id="demo-current-model-wait")
        loaded = current.get("modelLoaded") is True
        current_id = current.get("modelID")

        if not expected_loaded and not loaded:
            return current

        if expected_loaded and loaded:
            if expected_model_id is None:
                return current
            if isinstance(current_id, str) and current_id == expected_model_id:
                return current

        time.sleep(poll_interval_seconds)

    if expected_loaded:
        raise DemoError(
            f"モデルロード完了待ちがタイムアウトしました。expected_model_id={expected_model_id}"
        )
    raise DemoError("モデルアンロード完了待ちがタイムアウトしました。")


def load_model(client: VtsdClient, model_id: str, *, wait_timeout_seconds: float = 15.0) -> None:
    response = call_api(
        client,
        "ModelLoadRequest",
        data={"modelID": model_id},
        timeout_ms=5000,
        response_mode="data",
        client_request_id=f"demo-model-load-{model_id or 'unload'}",
    )
    require_ok(response, "ModelLoadRequest")
    if model_id:
        final = wait_for_model_state(
            client,
            expected_loaded=True,
            expected_model_id=model_id,
            timeout_seconds=wait_timeout_seconds,
        )
        print(
            f"[INFO] モデルロード完了: modelName={final.get('modelName')} modelID={final.get('modelID')}"
        )
        return

    wait_for_model_state(client, expected_loaded=False, timeout_seconds=wait_timeout_seconds)
    print("[INFO] モデルアンロード完了")


def ensure_model_loaded(client: VtsdClient, preferred_name: str) -> dict[str, Any]:
    current = call_api(
        client,
        "CurrentModelRequest",
        timeout_ms=5000,
        response_mode="data",
        client_request_id="demo-current-model",
    )
    current_data = require_ok(current, "CurrentModelRequest")
    if current_data.get("modelLoaded") is True:
        return current_data

    models = get_available_models(client)
    if not models:
        raise DemoError("ロード可能なモデルが見つかりません。")

    target = next((m for m in models if m.get("modelName") == preferred_name), models[0])
    target_id = target.get("modelID")
    if not isinstance(target_id, str):
        raise DemoError(f"modelID が不正です: {target}")
    print(f"[INFO] モデル '{target.get('modelName')}' をロードします。")
    load_model(client, target_id)
    return target


def move_model(
    client: VtsdClient,
    *,
    time_in_seconds: float,
    values_are_relative: bool,
    position_x: float | None = None,
    position_y: float | None = None,
    rotation: float | None = None,
    size: float | None = None,
    client_request_id: str,
) -> None:
    data: dict[str, Any] = {
        "timeInSeconds": time_in_seconds,
        "valuesAreRelativeToModel": values_are_relative,
    }
    if position_x is not None:
        data["positionX"] = position_x
    if position_y is not None:
        data["positionY"] = position_y
    if rotation is not None:
        data["rotation"] = rotation
    if size is not None:
        data["size"] = size

    response = call_api(
        client,
        "MoveModelRequest",
        data=data,
        timeout_ms=5000,
        response_mode="data",
        client_request_id=client_request_id,
    )
    require_ok(response, "MoveModelRequest")


def run_scenario_auth(
    *,
    managed_vtsd: ManagedVtsd,
    client: VtsdClient,
    broadcast_timeout_seconds: float,
    auth_timeout_seconds: float,
) -> str:
    print("\n### 1. 接続/認証デモ ###")
    print("1) VTSブロードキャストを受信して表示")
    broadcast = listen_vts_broadcast(broadcast_timeout_seconds, DEFAULT_BROADCAST_PORT)
    detected_port = broadcast.get("data", {}).get("port", managed_vtsd.vts_port)
    print(f"[INFO] BroadcastのWebSocketポート: {detected_port}")

    print("2) 取得した情報をもとに vtsd を起動して接続確認")
    if isinstance(detected_port, int) and detected_port != managed_vtsd.vts_port:
        print(f"[INFO] vtsd接続ポートを {managed_vtsd.vts_port} -> {detected_port} に更新します。")
        managed_vtsd.update_port(detected_port)
    managed_vtsd.start(REPO_ROOT)
    wait_until_ready(client, timeout_seconds=20.0)

    print("3) トークン未所持前提で認証要求")
    print("4) VTSの承認待ち（タイムアウト30秒）")
    token = request_token_and_authenticate(
        client,
        plugin_name="vtsd-demo-auth",
        plugin_developer="vtsd-demo-auth",
        timeout_seconds=auth_timeout_seconds,
    )

    print("5) API実行で成否確認")
    state_response = call_api(
        client,
        "APIStateRequest",
        timeout_ms=5000,
        response_mode="data",
        client_request_id="demo-api-state-post-auth",
    )
    require_ok(state_response, "APIStateRequest(認証後)")

    print("6) vtsd停止")
    managed_vtsd.stop()
    sleep_seconds(1.0, "停止後待機")

    print("7) vtsd再起動")
    managed_vtsd.start(REPO_ROOT)
    wait_until_ready(client, timeout_seconds=20.0)

    print("8) 取得済みトークンで再認証")
    authenticate_with_token(
        client,
        token=token,
        plugin_name="vtsd-demo-auth",
        plugin_developer="vtsd-demo-auth",
    )

    print("9) 認証成否を出力")
    state = call_api(
        client,
        "APIStateRequest",
        timeout_ms=5000,
        response_mode="data",
        client_request_id="demo-api-state-final",
    )
    final_state = require_ok(state, "APIStateRequest(最終)")
    print(f"[RESULT] currentSessionAuthenticated={final_state.get('currentSessionAuthenticated')}")
    return token


def run_scenario_model_load(client: VtsdClient, interval_seconds: float, auth_timeout_seconds: float) -> None:
    print("\n### 2. キャラクターロードデモ ###")
    wait_until_ready(client, timeout_seconds=20.0)
    ensure_session_authenticated(
        client,
        plugin_name="vtsd-demo-model-load",
        plugin_developer="vtsd-demo-model-load",
        auth_timeout_seconds=auth_timeout_seconds,
    )
    models = get_available_models(client)
    dump("使用可能モデル一覧", {"count": len(models), "availableModels": models})
    if not models:
        raise DemoError("使用可能モデルがありません。")

    for model in models:
        model_id = model.get("modelID")
        model_name = model.get("modelName", "<unknown>")
        if not isinstance(model_id, str):
            continue
        print(f"[INFO] ロード: {model_name} ({model_id})")
        load_model(client, model_id)
        sleep_seconds(interval_seconds, "ロード状態維持")
        print(f"[INFO] アンロード: {model_name}")
        load_model(client, "")
        sleep_seconds(interval_seconds, "アンロード後待機")


def run_scenario_hotkey(
    client: VtsdClient, interval_seconds: float, model_name: str, auth_timeout_seconds: float
) -> None:
    print("\n### 3. HotKey実行デモ ###")
    wait_until_ready(client, timeout_seconds=20.0)
    ensure_session_authenticated(
        client,
        plugin_name="vtsd-demo-hotkey",
        plugin_developer="vtsd-demo-hotkey",
        auth_timeout_seconds=auth_timeout_seconds,
    )
    ensure_model_loaded(client, model_name)

    response = call_api(
        client,
        "HotkeysInCurrentModelRequest",
        timeout_ms=5000,
        response_mode="data",
        client_request_id="demo-hotkeys-list",
    )
    data = require_ok(response, "HotkeysInCurrentModelRequest")
    hotkeys = data.get("availableHotkeys")
    if not isinstance(hotkeys, list) or not hotkeys:
        raise DemoError("ホットキーが見つかりません。")
    dump("HotKey一覧", {"count": len(hotkeys), "availableHotkeys": hotkeys})

    for hotkey in hotkeys:
        hotkey_id = hotkey.get("hotkeyID")
        hotkey_name = hotkey.get("name", "<unknown>")
        if not isinstance(hotkey_id, str) or not hotkey_id:
            continue
        print(f"[INFO] HotKey実行: {hotkey_name} ({hotkey_id})")
        cast_response = cast_api(
            client,
            "HotkeyTriggerRequest",
            data={"hotkeyID": hotkey_id},
            client_request_id=f"demo-hotkey-{hotkey_id}",
        )
        if cast_response.get("accepted") is not True:
            raise DemoError(f"HotkeyTriggerRequest が受理されませんでした: {cast_response}")
        sleep_seconds(interval_seconds, "次のHotKeyまで待機")


def run_scenario_move(
    client: VtsdClient, move_pause_seconds: float, model_name: str, auth_timeout_seconds: float
) -> None:
    print("\n### 4. キャラクター移動デモ ###")
    wait_until_ready(client, timeout_seconds=20.0)
    ensure_session_authenticated(
        client,
        plugin_name="vtsd-demo-move",
        plugin_developer="vtsd-demo-move",
        auth_timeout_seconds=auth_timeout_seconds,
    )
    ensure_model_loaded(client, model_name)

    current = call_api(
        client,
        "CurrentModelRequest",
        timeout_ms=5000,
        response_mode="data",
        client_request_id="demo-current-model-before-move",
    )
    current_data = require_ok(current, "CurrentModelRequest(移動前)")
    position = current_data.get("modelPosition", {})
    base_size = position.get("size", 0.0)
    base_rotation = position.get("rotation", 0.0)
    if not isinstance(base_size, (int, float)):
        base_size = 0.0
    if not isinstance(base_rotation, (int, float)):
        base_rotation = 0.0

    corners = [
        (-0.8, 0.8),
        (0.8, 0.8),
        (0.8, -0.8),
        (-0.8, -0.8),
    ]
    for idx, (px, py) in enumerate(corners, start=1):
        print(f"[INFO] 四隅移動 {idx}: x={px}, y={py}")
        move_model(
            client,
            time_in_seconds=1.2,
            values_are_relative=False,
            position_x=px,
            position_y=py,
            client_request_id=f"demo-move-corner-{idx}",
        )
        sleep_seconds(move_pause_seconds, "次の移動まで待機")

    print("[INFO] 中心へ戻す")
    move_model(
        client,
        time_in_seconds=1.2,
        values_are_relative=False,
        position_x=0.0,
        position_y=0.0,
        client_request_id="demo-move-center",
    )
    sleep_seconds(move_pause_seconds, "サイズ変更前待機")

    print("[INFO] サイズ最小 -> 最大 -> デフォルト")
    for label, size in [("最小", -100.0), ("最大", 100.0), ("デフォルト", float(base_size))]:
        move_model(
            client,
            time_in_seconds=1.0,
            values_are_relative=False,
            size=size,
            client_request_id=f"demo-size-{label}",
        )
        sleep_seconds(move_pause_seconds, f"{label}サイズ反映待機")

    print("[INFO] ぐるっと回転")
    move_model(
        client,
        time_in_seconds=2.0,
        values_are_relative=True,
        rotation=360.0,
        client_request_id="demo-rotate-full",
    )
    sleep_seconds(move_pause_seconds, "回転後待機")

    print("[INFO] 回転を元に戻す")
    move_model(
        client,
        time_in_seconds=1.0,
        values_are_relative=False,
        rotation=float(base_rotation),
        client_request_id="demo-rotate-restore",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VTSデモシナリオ実行スクリプト")
    parser.add_argument(
        "--scenario",
        required=True,
        choices=["auth", "model-load", "hotkey", "move", "all"],
        help="実行するデモシナリオ",
    )
    parser.add_argument("--pipe-name", default=DEFAULT_PIPE_NAME, help="vtsdのNamed Pipe名")
    parser.add_argument(
        "--vts-port",
        type=int,
        default=DEFAULT_VTS_PORT,
        help="VTS WebSocketポート。authシナリオでは受信Broadcastと一致している必要があります。",
    )
    parser.add_argument("--broadcast-timeout", type=float, default=10.0, help="Broadcast待機秒数")
    parser.add_argument("--auth-timeout", type=float, default=30.0, help="認証承認待機秒数")
    parser.add_argument("--step-interval", type=float, default=5.0, help="各デモ手順の待機秒数")
    parser.add_argument("--model-name", default="Akari", help="HotKey/Moveデモで優先ロードするモデル名")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    managed_vtsd = ManagedVtsd.create(pipe_name=args.pipe_name, vts_port=args.vts_port)
    client = VtsdClient(pipe_name=args.pipe_name)

    try:
        if args.scenario == "auth":
            run_scenario_auth(
                managed_vtsd=managed_vtsd,
                client=client,
                broadcast_timeout_seconds=args.broadcast_timeout,
                auth_timeout_seconds=args.auth_timeout,
            )
            return 0

        if args.scenario == "model-load":
            managed_vtsd.start(REPO_ROOT)
            run_scenario_model_load(client, args.step_interval, args.auth_timeout)
            return 0
        if args.scenario == "hotkey":
            managed_vtsd.start(REPO_ROOT)
            run_scenario_hotkey(client, args.step_interval, args.model_name, args.auth_timeout)
            return 0
        if args.scenario == "move":
            managed_vtsd.start(REPO_ROOT)
            run_scenario_move(client, args.step_interval, args.model_name, args.auth_timeout)
            return 0

        run_scenario_auth(
            managed_vtsd=managed_vtsd,
            client=client,
            broadcast_timeout_seconds=args.broadcast_timeout,
            auth_timeout_seconds=args.auth_timeout,
        )
        run_scenario_model_load(client, args.step_interval, args.auth_timeout)
        run_scenario_hotkey(client, args.step_interval, args.model_name, args.auth_timeout)
        run_scenario_move(client, args.step_interval, args.model_name, args.auth_timeout)
        return 0
    except DemoError as exc:
        print(f"[ERROR] {exc}")
        return 1
    finally:
        managed_vtsd.stop()


if __name__ == "__main__":
    raise SystemExit(main())
