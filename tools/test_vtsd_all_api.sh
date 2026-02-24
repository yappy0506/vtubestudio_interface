#!/usr/bin/env bash
set -euo pipefail

# vtsd 経由で VTube Studio Public API の messageType を一括検証するシェルスクリプト。
# - スクリプト本体は sh/bash で提供（要件対応）
# - Named Pipe 通信は既存 Python クライアント(vtsd_client.py)を内部で呼び出す
#
# 使い方:
#   bash tools/test_vtsd_all_api.sh --mode call
#   bash tools/test_vtsd_all_api.sh --mode cast --pipe "\\\\.\\pipe\\vtsd"
#   bash tools/test_vtsd_all_api.sh --mode call --filter Authentication
#
# 終了コード:
#   0: 全件 PASS
#   1: FAIL あり
#   2: 実行エラー

MODE="call"
PIPE_NAME='\\.\pipe\vtsd'
TIMEOUT_MS=3000
FILTER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"; shift 2 ;;
    --pipe)
      PIPE_NAME="$2"; shift 2 ;;
    --timeout-ms)
      TIMEOUT_MS="$2"; shift 2 ;;
    --filter)
      FILTER="$2"; shift 2 ;;
    -h|--help)
      sed -n '1,30p' "$0"
      exit 0 ;;
    *)
      echo "[ERROR] 未知の引数: $1" >&2
      exit 2 ;;
  esac
done

if [[ "$MODE" != "call" && "$MODE" != "cast" ]]; then
  echo "[ERROR] --mode は call または cast を指定してください" >&2
  exit 2
fi

# VTS Public API の主要カテゴリを含む messageType 一覧（全件試行用）
# 注: API バージョン差異で未対応 messageType がある場合は FAIL として報告されます。
readarray -t MESSAGE_TYPES <<'LIST'
APIStateRequest
AuthenticationTokenRequest
AuthenticationRequest
StatisticsRequest
VTSFolderInfoRequest
CurrentModelRequest
AvailableModelsRequest
ModelLoadRequest
MoveModelRequest
HotkeysInCurrentModelRequest
HotkeyTriggerRequest
ExpressionStateRequest
ExpressionActivationRequest
ArtMeshListRequest
ColorTintRequest
SceneColorOverlayInfoRequest
FaceFoundRequest
InputParameterListRequest
ParameterValueRequest
Live2DParameterListRequest
ParameterCreationRequest
ParameterDeletionRequest
InjectParameterDataRequest
GetCurrentModelPhysicsRequest
SetCurrentModelPhysicsRequest
NDIConfigRequest
ItemListRequest
ItemLoadRequest
ItemUnloadRequest
ItemAnimationControlRequest
ItemMoveRequest
EventSubscriptionRequest
LIST

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PASS=0
FAIL=0

run_one() {
  local message_type="$1"

  local output
  if ! output="$(cd "$REPO_ROOT" && python - "$MODE" "$PIPE_NAME" "$TIMEOUT_MS" "$message_type" <<'PY'
import json
import sys
from pathlib import Path

repo = Path.cwd()
sys.path.insert(0, str(repo))
from vtsd_client import VtsdClient

mode = sys.argv[1]
pipe_name = sys.argv[2]
timeout_ms = int(sys.argv[3])
message_type = sys.argv[4]

client = VtsdClient(pipe_name=pipe_name)

# データ必須API向けに最小ダミーを用意
payloads = {
    "AuthenticationTokenRequest": {"pluginName": "vtsd-test", "pluginDeveloper": "vtsd-test"},
    "AuthenticationRequest": {
        "pluginName": "vtsd-test",
        "pluginDeveloper": "vtsd-test",
        "authenticationToken": "DUMMY_TOKEN"
    },
    "ModelLoadRequest": {"modelID": "DUMMY_MODEL_ID"},
    "MoveModelRequest": {},
    "HotkeyTriggerRequest": {"hotkeyID": "DUMMY_HOTKEY"},
    "ExpressionActivationRequest": {"expressionFile": "DUMMY", "active": True},
    "ColorTintRequest": {},
    "ParameterValueRequest": {"name": "ParamAngleX"},
    "ParameterCreationRequest": {"parameterName": "test_param"},
    "ParameterDeletionRequest": {"parameterName": "test_param"},
    "InjectParameterDataRequest": {"parameterValues": []},
    "SetCurrentModelPhysicsRequest": {},
    "NDIConfigRequest": {},
    "ItemLoadRequest": {"fileName": "DUMMY_ITEM"},
    "ItemUnloadRequest": {"instanceID": "DUMMY_INSTANCE"},
    "ItemAnimationControlRequest": {"instanceID": "DUMMY_INSTANCE", "framerate": 0, "frame": 0},
    "ItemMoveRequest": {"itemsToMove": []},
    "EventSubscriptionRequest": {"eventName": "ModelLoadedEvent", "subscribe": True},
}

data = payloads.get(message_type)

if mode == "call":
    resp = client.call(message_type, data=data, timeoutMs=timeout_ms, responseMode="raw", clientRequestId=f"allapi-{message_type}")
else:
    resp = client.cast(message_type, data=data, clientRequestId=f"allapi-{message_type}")

print(json.dumps(resp, ensure_ascii=False))
PY
)"; then
    echo "[FAIL] $message_type :: 実行失敗"
    FAIL=$((FAIL+1))
    return
  fi

  # 判定方針:
  # - call: ok=true もしくは error.code を受理 (疎通確認)
  # - cast: ok=true が返れば受理（accepted true/false は状態依存）
  local is_pass=1
  if [[ "$MODE" == "call" ]]; then
    if [[ "$output" == *'"ok": true'* || "$output" == *'"error": {'* ]]; then
      is_pass=0
    fi
  else
    if [[ "$output" == *'"ok": true'* ]]; then
      is_pass=0
    fi
  fi

  if [[ $is_pass -eq 0 ]]; then
    echo "[PASS] $message_type :: $output"
    PASS=$((PASS+1))
  else
    echo "[FAIL] $message_type :: $output"
    FAIL=$((FAIL+1))
  fi
}

echo "[INFO] mode=$MODE pipe=$PIPE_NAME timeoutMs=$TIMEOUT_MS"

for mt in "${MESSAGE_TYPES[@]}"; do
  if [[ -n "$FILTER" && "$mt" != *"$FILTER"* ]]; then
    continue
  fi
  run_one "$mt"
done

echo

echo "[SUMMARY] PASS=$PASS FAIL=$FAIL"

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
