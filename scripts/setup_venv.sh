#!/usr/bin/env bash
set -euo pipefail

# vtsd 用の仮想環境を作成し、依存をインストールするスクリプト
# 使い方:
#   bash scripts/setup_venv.sh
#   bash scripts/setup_venv.sh --venv .venv --python python3.11
#   bash scripts/setup_venv.sh --no-install

VENV_DIR=".venv"
PYTHON_CMD="python"
INSTALL_DEPS=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv)
      VENV_DIR="$2"
      shift 2
      ;;
    --python)
      PYTHON_CMD="$2"
      shift 2
      ;;
    --no-install)
      INSTALL_DEPS=0
      shift
      ;;
    *)
      echo "[ERROR] 未知の引数: $1" >&2
      exit 1
      ;;
  esac
done

if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
  echo "[ERROR] Python コマンドが見つかりません: $PYTHON_CMD" >&2
  exit 1
fi

echo "[INFO] 仮想環境を作成します: $VENV_DIR"
"$PYTHON_CMD" -m venv "$VENV_DIR"

if [[ -f "$VENV_DIR/Scripts/activate" ]]; then
  # Windows (Git Bash) 想定
  # shellcheck disable=SC1090
  source "$VENV_DIR/Scripts/activate"
elif [[ -f "$VENV_DIR/bin/activate" ]]; then
  # Linux/macOS
  # shellcheck disable=SC1090
  source "$VENV_DIR/bin/activate"
else
  echo "[ERROR] activate スクリプトが見つかりません" >&2
  exit 1
fi

echo "[INFO] Python: $(python --version)"

echo "[INFO] pip/setuptools/wheel を更新します"
python -m pip install --upgrade pip setuptools wheel

if [[ "$INSTALL_DEPS" -eq 1 ]]; then
  echo "[INFO] requirements.txt から依存をインストールします"
  python -m pip install -r requirements.txt
else
  echo "[INFO] --no-install が指定されたため依存インストールをスキップします"
fi

echo "[INFO] 完了: 仮想環境 $VENV_DIR"
