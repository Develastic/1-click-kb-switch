@echo off
where cargo >nul 2>nul
if errorlevel 1 (
  echo Rust toolchain not found in PATH.
  exit /b 1
)

cargo run -p one-click-kb-switch
