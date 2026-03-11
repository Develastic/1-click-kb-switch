#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

BOTTLES_ROOT="/home/mykola/sysadmin/bottles"
RUN_PROJECT_CMD="$BOTTLES_ROOT/run-project-cmd.sh"
PROJECT_ROOT="$(pwd)"
PROJECT_NAME="1-click-kb-switch"
STAGE_DIR="C:\\build\\${PROJECT_NAME}-stage"
STAGE_DIR_HOST="$HOME/.var/app/com.usebottles.bottles/data/bottles/bottles/win-build-main/drive_c/build/${PROJECT_NAME}-stage"
OUTPUT_DIR="$PROJECT_ROOT/output/windows"

if [[ ! -x "$RUN_PROJECT_CMD" ]]; then
  echo "Bottles helper not found: $RUN_PROJECT_CMD" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
mkdir -p "$(dirname "$STAGE_DIR_HOST")"

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync is required for Bottles staging builds." >&2
  exit 1
fi

rsync -a --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'build/' \
  --exclude 'dist/' \
  --exclude 'output/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '.mypy_cache/' \
  --exclude '*.egg-info/' \
  "$PROJECT_ROOT/" "$STAGE_DIR_HOST/"

VERSION=$(uv run python - <<'PY'
import tomllib
from pathlib import Path
print(tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])
PY
)

cat > "$STAGE_DIR_HOST/build-inside-bottle.cmd" <<CMD
@echo on
cd /d ${STAGE_DIR}
C:\tools\uv\uv.exe python install 3.12
if errorlevel 1 exit /b %errorlevel%
if not exist C:\uv-cache\1-click-kb-switch mkdir C:\uv-cache\1-click-kb-switch
set "UV_LINK_MODE=copy"
set "UV_CACHE_DIR=C:\uv-cache\1-click-kb-switch"
C:\tools\uv\uv.exe sync --extra dev --python 3.12 --link-mode copy
if errorlevel 1 exit /b %errorlevel%
.venv\Scripts\python.exe -m pytest
if errorlevel 1 exit /b %errorlevel%
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath dist-windows --workpath build-windows packaging\windows\one_click_kb_switch.spec
if errorlevel 1 exit /b %errorlevel%
set "APP_VERSION=${VERSION}"
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\windows\installer.iss
if errorlevel 1 exit /b %errorlevel%
CMD

"$RUN_PROJECT_CMD" "$PROJECT_ROOT" "cd /d ${STAGE_DIR} && build-inside-bottle.cmd"

cp "$STAGE_DIR_HOST/output/1-click-kb-switch-setup.exe" "$OUTPUT_DIR/1-click-kb-switch-setup.exe"

echo "Built Windows installer: $OUTPUT_DIR/1-click-kb-switch-setup.exe"
