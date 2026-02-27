# vtsd (VTube Studio IPC daemon)

## 概要
`vtsd` は Windows Named Pipe (`\\.\pipe\vtsd`) で NDJSON を受け取り、VTube Studio Public API (WebSocket) へ中継するデーモンです。

- `cast`: 即時 ACK（VTS 応答待ちなし）
- `call`: 応答待ち（`responseMode=raw|data`）
- 認証はセッション単位で管理（接続時に確立）

## 起動方法
```bash
python -m vtsd
```

設定ファイルを指定する場合:
```bash
python -m vtsd --config .\vtsd.json
```

## 設定ファイル (`vtsd.json`)
```json
{
  "pipe_name": "\\\\.\\pipe\\vtsd",
  "vts_host": "localhost",
  "vts_port": 8001,
  "default_call_timeout_ms": 5000,
  "max_queue_size": 1024,
  "auto_token_request": false,
  "token_path": "%APPDATA%\\vtsd\\token.txt",
  "reconnect_backoff_ms": { "min": 300, "max": 5000 }
}
```

## 呼び出し例（Python）
```python
from vtsd_client import VtsdClient

client = VtsdClient()

# call
resp = client.call("APIStateRequest", responseMode="data")
print(resp)

# cast
resp = client.cast("HotkeyTriggerRequest", {"hotkeyID": "abc"})
print(resp)
```

## デモシナリオ実行
`docs/demo_scenario.md` の手順を実行するデモスクリプトです。

前提:
- VTube Studio を起動していること
- 初回認証時は VTube Studio 側でプラグイン許可操作を行うこと

```bash
# 1. 接続/認証デモ
python demo/run_demo_scenarios.py --scenario auth

# 2. キャラクターロードデモ
python demo/run_demo_scenarios.py --scenario model-load

# 3. HotKey実行デモ
python demo/run_demo_scenarios.py --scenario hotkey --model-name Akari

# 4. キャラクター移動デモ
python demo/run_demo_scenarios.py --scenario move --model-name Akari

# 1〜4を連続実行
python demo/run_demo_scenarios.py --scenario all
```

主なオプション:
- `--pipe-name`: vtsd の Named Pipe 名（既定 `\\.\pipe\vtsd-demo`）
- `--vts-port`: VTS WebSocket ポート（既定 `8001`）
- `--auth-timeout`: 認証承認待機秒数（既定 `30`）
- `--step-interval`: デモ内の待機秒数（既定 `5`）

## 開発用仮想環境セットアップ

```bash
# 仮想環境作成 + 依存インストール
bash scripts/setup_venv.sh

# 依存インストールを行わず仮想環境だけ作成
bash scripts/setup_venv.sh --no-install

# 既定(.venv)を削除
bash scripts/clean_venv.sh
```

オプション:
- `--venv <path>`: 仮想環境ディレクトリを変更
- `--python <python_cmd>`: 使用する Python コマンドを変更（`setup_venv.sh` のみ）
