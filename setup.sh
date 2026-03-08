#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
rm -rf .venv
uv venv --python 3.12 .venv
uv sync --extra dev
uv run python - <<'PY'
import tkinter
import pystray
print(f"Tk version: {tkinter.TkVersion}")
print(f"Tray backend: {pystray.Icon.__module__}")
PY
