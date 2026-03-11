param(
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

uv run python -c "import tkinter; print(f'Tk version: {tkinter.TkVersion}')"
if (-not $SkipTests) {
    uv run pytest
}
uv run pyinstaller packaging/windows/one_click_kb_switch.spec --noconfirm --clean --distpath dist-windows --workpath build-windows
$version = uv run python -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])"
$env:APP_VERSION = $version
$inno = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
if (!(Test-Path $inno)) {
    throw 'Inno Setup 6 was not found at C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
}
& $inno packaging\windows\installer.iss
New-Item -ItemType Directory -Force output\windows | Out-Null
Copy-Item output\1-click-kb-switch-setup.exe output\windows\1-click-kb-switch-setup.exe -Force
