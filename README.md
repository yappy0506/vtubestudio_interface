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

## 疎通確認

### クイックチェック
```bash
python tools/test_vtsd_pipe.py
```

### APIフロー確認（推奨）
```bash
# VTS未起動時
python tools/test_vtsd_api_flow.py --scenario disconnected

# VTS起動・接続済み時
python tools/test_vtsd_api_flow.py --scenario connected

# VTS起動・未認証セッション時
python tools/test_vtsd_api_flow.py --scenario auth-required
```

`tools/test_vtsd_api_flow.py` は以下を確認します。
- `cast` 未接続時の `accepted=false, reason=VTS_NOT_CONNECTED`
- `call` 未接続時の `error.code=VTS_NOT_CONNECTED`
- `call APIStateRequest` の `responseMode=data/raw` の差異
- 未認証セッション時の `AUTH_REQUIRED`（cast/call）


### 全API一括テスト（sh）
```bash
# call で全API messageType を順に検証
bash tools/test_vtsd_all_api.sh --mode call

# cast で全API messageType を順に検証
bash tools/test_vtsd_all_api.sh --mode cast

# 一部だけ実行（例: Authentication を含む messageType）
bash tools/test_vtsd_all_api.sh --mode call --filter Authentication
```

`tools/test_vtsd_all_api.sh` は **シェルスクリプト**として実装されており、
VTS Public API の messageType を全件順次実行して結果を集計します。
（注: Named Pipe 接続が前提のため、実行は Windows + vtsd 起動環境で行ってください）


## 開発用仮想環境セットアップ

```bash
# 仮想環境作成 + 依存インストール
bash tools/setup_venv.sh

# 依存インストールを行わず仮想環境だけ作成
bash tools/setup_venv.sh --no-install

# 既定(.venv)を削除
bash tools/clean_venv.sh
```

オプション:
- `--venv <path>`: 仮想環境ディレクトリを変更
- `--python <python_cmd>`: 使用する Python コマンドを変更（`setup_venv.sh` のみ）
