from __future__ import annotations

"""vtsd の主要API動作をまとめて確認するテストスクリプト。

前提:
- vtsd が起動済みであること
- 実際の VTS 状態に応じて、実行するシナリオを切り替えること

例:
  # VTS未起動時（cast の VTS_NOT_CONNECTED を確認）
  python tools/test_vtsd_api_flow.py --scenario disconnected

  # VTS起動・接続済み時（call 成功、responseMode差異を確認）
  python tools/test_vtsd_api_flow.py --scenario connected

  # VTS起動・未認証セッション時（AUTH_REQUIRED を確認）
  python tools/test_vtsd_api_flow.py --scenario auth-required
"""

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vtsd_client import VtsdClient


@dataclass(slots=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def _dump(title: str, payload: dict[str, Any]) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _is_error_code(resp: dict[str, Any], code: str) -> bool:
    return (resp.get("ok") is False) and resp.get("error", {}).get("code") == code


def _is_cast_reason(resp: dict[str, Any], reason: str) -> bool:
    return (
        resp.get("ok") is True
        and resp.get("accepted") is False
        and resp.get("reason") == reason
    )


def scenario_disconnected(client: VtsdClient) -> list[CheckResult]:
    results: list[CheckResult] = []

    cast_resp = client.cast(
        "HotkeyTriggerRequest",
        {"hotkeyID": "dummy"},
        clientRequestId="flow-disconnected-cast",
    )
    _dump("cast HotkeyTriggerRequest", cast_resp)
    results.append(
        CheckResult(
            name="VTS未接続時 cast は accepted=false / VTS_NOT_CONNECTED",
            ok=_is_cast_reason(cast_resp, "VTS_NOT_CONNECTED"),
            detail="expected accepted=false reason=VTS_NOT_CONNECTED",
        )
    )

    call_resp = client.call(
        "APIStateRequest",
        responseMode="raw",
        timeoutMs=1500,
        clientRequestId="flow-disconnected-call",
    )
    _dump("call APIStateRequest", call_resp)
    results.append(
        CheckResult(
            name="VTS未接続時 call は VTS_NOT_CONNECTED",
            ok=_is_error_code(call_resp, "VTS_NOT_CONNECTED"),
            detail="expected error.code=VTS_NOT_CONNECTED",
        )
    )

    return results


def scenario_connected(client: VtsdClient) -> list[CheckResult]:
    results: list[CheckResult] = []

    call_data = client.call(
        "APIStateRequest",
        responseMode="data",
        timeoutMs=3000,
        clientRequestId="flow-connected-call-data",
    )
    _dump("call APIStateRequest (responseMode=data)", call_data)
    results.append(
        CheckResult(
            name="responseMode=data は result に data 部分のみ返る",
            ok=call_data.get("ok") is True and isinstance(call_data.get("result"), dict),
            detail="expected ok=true and result is dict(data)",
        )
    )

    call_raw = client.call(
        "APIStateRequest",
        responseMode="raw",
        timeoutMs=3000,
        clientRequestId="flow-connected-call-raw",
    )
    _dump("call APIStateRequest (responseMode=raw)", call_raw)
    results.append(
        CheckResult(
            name="responseMode=raw は messageType を含む生レスポンスを返る",
            ok=call_raw.get("ok") is True and isinstance(call_raw.get("result"), dict) and "messageType" in call_raw.get("result", {}),
            detail="expected ok=true and result.messageType exists",
        )
    )

    cast_resp = client.cast(
        "APIStateRequest",
        clientRequestId="flow-connected-cast-api-state",
    )
    _dump("cast APIStateRequest", cast_resp)
    results.append(
        CheckResult(
            name="接続済みかつ APIStateRequest cast は accepted=true",
            ok=cast_resp.get("ok") is True and cast_resp.get("accepted") is True,
            detail="expected ok=true accepted=true",
        )
    )

    return results


def scenario_auth_required(client: VtsdClient) -> list[CheckResult]:
    results: list[CheckResult] = []

    cast_resp = client.cast(
        "HotkeyTriggerRequest",
        {"hotkeyID": "dummy"},
        clientRequestId="flow-auth-required-cast",
    )
    _dump("cast HotkeyTriggerRequest", cast_resp)
    results.append(
        CheckResult(
            name="未認証セッションの cast は AUTH_REQUIRED",
            ok=_is_cast_reason(cast_resp, "AUTH_REQUIRED"),
            detail="expected accepted=false reason=AUTH_REQUIRED",
        )
    )

    call_resp = client.call(
        "HotkeyTriggerRequest",
        {"hotkeyID": "dummy"},
        timeoutMs=1500,
        clientRequestId="flow-auth-required-call",
    )
    _dump("call HotkeyTriggerRequest", call_resp)
    results.append(
        CheckResult(
            name="未認証セッションの call は AUTH_REQUIRED",
            ok=_is_error_code(call_resp, "AUTH_REQUIRED"),
            detail="expected error.code=AUTH_REQUIRED",
        )
    )

    return results


def print_summary(results: list[CheckResult]) -> int:
    print("\n=== Summary ===")
    failed = 0
    for result in results:
        mark = "PASS" if result.ok else "FAIL"
        print(f"[{mark}] {result.name} ({result.detail})")
        if not result.ok:
            failed += 1

    if failed:
        print(f"\n{failed} check(s) failed.")
        return 1

    print("\nAll checks passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="vtsd API flow checker")
    parser.add_argument(
        "--scenario",
        required=True,
        choices=["disconnected", "connected", "auth-required"],
        help="実行するシナリオ",
    )
    parser.add_argument("--pipe-name", default=r"\\.\pipe\vtsd", help="vtsd の Named Pipe 名")
    args = parser.parse_args()

    client = VtsdClient(pipe_name=args.pipe_name)

    if args.scenario == "disconnected":
        return print_summary(scenario_disconnected(client))
    if args.scenario == "connected":
        return print_summary(scenario_connected(client))
    return print_summary(scenario_auth_required(client))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] 実行失敗: {exc}")
        raise
