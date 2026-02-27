#!/usr/bin/env bash
set -euo pipefail

# vtsd 用の仮想環境を削除するスクリプト
# 使い方:
#   bash scripts/clean_venv.sh
#   bash scripts/clean_venv.sh --venv .venv

VENV_DIR=".venv"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv)
      VENV_DIR="$2"
      shift 2
      ;;
    *)
      echo "[ERROR] 未知の引数: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -d "$VENV_DIR" ]]; then
  rm -rf "$VENV_DIR"
  echo "[INFO] 削除しました: $VENV_DIR"
else
  echo "[INFO] 対象が存在しないためスキップ: $VENV_DIR"
fi
