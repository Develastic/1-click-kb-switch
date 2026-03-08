param(
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

uv run python -c "import tkinter; print(f'Tk version: {tkinter.TkVersion}')"
if (-not $SkipTests) {
    uv run pytest
}
uv run pyinstaller packaging/windows/one_click_kb_switch.spec --noconfirm --clean

$wixBin = $env:WIX
if (-not $wixBin) {
    $wixBin = 'C:\Program Files (x86)\WiX Toolset v3.11\bin'
}
$heat = Join-Path $wixBin 'heat.exe'
$candle = Join-Path $wixBin 'candle.exe'
$light = Join-Path $wixBin 'light.exe'
if (!(Test-Path $heat) -or !(Test-Path $candle) -or !(Test-Path $light)) {
    throw 'WiX Toolset v3 was not found. Install WiX or set WIX to its bin directory.'
}

$version = uv run python -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8')).get('project', {}).get('version'))"
New-Item -ItemType Directory -Force build\wix | Out-Null
New-Item -ItemType Directory -Force dist\release-assets | Out-Null

& $heat dir dist\1-Click-KB-Switch -cg AppFiles -dr INSTALLDIR -gg -g1 -srd -out build\wix\app-files.wxs
& $candle -dProductVersion=$version packaging\windows\installer.wxs build\wix\app-files.wxs -ext WixUIExtension -ext WixUtilExtension -out build\wix\
& $light build\wix\installer.wixobj build\wix\app-files.wixobj -ext WixUIExtension -ext WixUtilExtension -o dist\release-assets\1-Click-KB-Switch.msi
Copy-Item dist\1-Click-KB-Switch\* dist\release-assets\ -Recurse -Force
Copy-Item README.md, LICENSE, EULA.md dist\release-assets\
if (Test-Path dist\release-assets\SHA256SUMS.txt) { Remove-Item dist\release-assets\SHA256SUMS.txt }
Get-ChildItem dist\release-assets | ForEach-Object {
    $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    "$hash  $($_.Name)" | Add-Content dist\release-assets\SHA256SUMS.txt
}
