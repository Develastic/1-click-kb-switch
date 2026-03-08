#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
uv run python - <<'PY'
import tkinter
print(f"Tk version: {tkinter.TkVersion}")
PY
uv run pyinstaller packaging/linux/appimage/one_click_kb_switch.spec --noconfirm --clean
mkdir -p dist/appimage-root/usr/bin
cp -r dist/1-Click-KB-Switch/* dist/appimage-root/usr/bin/
cp packaging/linux/appimage/1-click-kb-switch.desktop dist/appimage-root/
cp packaging/linux/appimage/apprun dist/appimage-root/AppRun
chmod +x dist/appimage-root/AppRun
if [[ -z "${APPIMAGETOOL:-}" ]]; then
  echo "APPIMAGETOOL is not set. Download appimagetool and export APPIMAGETOOL=/path/to/appimagetool" >&2
  exit 1
fi
"$APPIMAGETOOL" dist/appimage-root dist/1-Click-KB-Switch.AppImage
