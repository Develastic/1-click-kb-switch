param(
    [switch]$SkipTests
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Invoke-Native {
    param([Parameter(Mandatory = $true)][string[]]$Command)
    & $Command[0] $Command[1..($Command.Length - 1)]
    if ($LASTEXITCODE -ne 0) {
        throw ("Command failed with exit code {0}: {1}" -f $LASTEXITCODE, ($Command -join " "))
    }
}

Invoke-Native @('uv', 'sync', '--extra', 'dev')
Invoke-Native @('uv', 'run', 'python', '-c', "import tkinter; print(f'Tk version: {tkinter.TkVersion}')")
if (-not $SkipTests) {
    Invoke-Native @('uv', 'run', 'pytest')
}
Invoke-Native @('uv', 'run', 'pyinstaller', 'packaging/windows/one_click_kb_switch.spec', '--noconfirm', '--clean', '--distpath', 'dist-windows', '--workpath', 'build-windows')
$version = uv run python -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8'))['project']['version'])"
if ($LASTEXITCODE -ne 0) {
    throw 'Failed to read application version from pyproject.toml'
}
$env:APP_VERSION = $version.Trim()
$inno = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
if (!(Test-Path $inno)) {
    throw 'Inno Setup 6 was not found at C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
}
Invoke-Native @($inno, 'packaging\windows\installer.iss')
New-Item -ItemType Directory -Force output\windows | Out-Null
Copy-Item output\1-click-kb-switch-setup.exe output\windows\1-click-kb-switch-setup.exe -Force
