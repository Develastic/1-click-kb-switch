@echo off
where go >nul 2>nul
if errorlevel 1 (
  echo Go toolchain not found in PATH.
  exit /b 1
)

go version
go mod download
