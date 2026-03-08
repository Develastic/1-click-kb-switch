@echo off
setlocal
cd /d %~dp0
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1 %*
