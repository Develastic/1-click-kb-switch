@echo off
setlocal
cd /d %~dp0
if exist .venv rmdir /s /q .venv
uv venv --python 3.12 .venv
if errorlevel 1 exit /b 1
uv sync --extra dev
if errorlevel 1 exit /b 1
uv run python -c "import tkinter, pystray; print(f'Tk version: {tkinter.TkVersion}'); print(f'Tray backend: {pystray.Icon.__module__}')"
