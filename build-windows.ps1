param(
    [switch]$SkipTests,
    [switch]$SkipMsi,
    [switch]$SkipChecksums,
    [string]$Target = "x86_64-pc-windows-msvc"
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name, [string]$Hint)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name not found. $Hint"
    }
}

function Get-VersionFromCargoToml {
    param([string]$Path)
    $match = Select-String -Path $Path -Pattern '^version\s*=\s*"([^"]+)"' | Select-Object -First 1
    if (-not $match) {
        throw "Unable to read version from $Path"
    }
    return $match.Matches[0].Groups[1].Value
}

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Require-Command cargo "Install Rust via rustup first."
Require-Command cargo-wix "Install cargo-wix: cargo install cargo-wix --version 0.3.9 --locked"
Require-Command candle "Install WiX Toolset v3 and ensure candle.exe is in PATH."
Require-Command light "Install WiX Toolset v3 and ensure light.exe is in PATH."

$Version = Get-VersionFromCargoToml -Path (Join-Path $RepoRoot "app/Cargo.toml")
$ReleaseAssetsDir = Join-Path $RepoRoot "target/release-assets"
$WixOutputDir = Join-Path $RepoRoot "target/wix"
$BinaryDir = Join-Path $RepoRoot "target/$Target/release"
$BinaryPath = Join-Path $BinaryDir "one-click-kb-switch.exe"
$NotesTemplatePath = Join-Path $RepoRoot ".github/release/windows-release-notes-template.md"
$NotesPath = Join-Path $ReleaseAssetsDir "RELEASE_NOTES.md"
$ChecksumPath = Join-Path $ReleaseAssetsDir "SHA256SUMS.txt"

Write-Host "==> Repo root: $RepoRoot"
Write-Host "==> Target: $Target"
Write-Host "==> Version: $Version"

if (-not $SkipTests) {
    Write-Host "==> Running tests"
    cargo test --workspace
}

Write-Host "==> Building release binary"
cargo build --workspace --release --target $Target

if (-not (Test-Path $BinaryPath)) {
    throw "Release binary not found at $BinaryPath"
}

New-Item -ItemType Directory -Force -Path $ReleaseAssetsDir | Out-Null
New-Item -ItemType Directory -Force -Path $WixOutputDir | Out-Null

Write-Host "==> Copying EXE and metadata into release-assets"
Copy-Item $BinaryPath $ReleaseAssetsDir -Force
Copy-Item (Join-Path $RepoRoot "README.md") $ReleaseAssetsDir -Force
Copy-Item (Join-Path $RepoRoot "LICENSE") $ReleaseAssetsDir -Force

$Notes = Get-Content $NotesTemplatePath -Raw
$Notes = $Notes.Replace('{{version}}', $Version)
Set-Content -Path $NotesPath -Value $Notes

if (-not $SkipMsi) {
    Write-Host "==> Building MSI installer"
    Push-Location (Join-Path $RepoRoot "app")
    try {
        cargo wix --package one-click-kb-switch --target $Target --output ../target/wix/
    }
    finally {
        Pop-Location
    }

    $Msi = Get-ChildItem -Path $WixOutputDir -Filter *.msi | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $Msi) {
        throw "MSI was not created in $WixOutputDir"
    }
    Copy-Item $Msi.FullName $ReleaseAssetsDir -Force
    Write-Host "==> MSI: $($Msi.FullName)"
    Write-Host "==> MSI size: $([math]::Round($Msi.Length / 1MB, 2)) MiB"
}

if (-not $SkipChecksums) {
    Write-Host "==> Generating SHA256 checksums"
    if (Test-Path $ChecksumPath) {
        Remove-Item $ChecksumPath -Force
    }
    Get-ChildItem $ReleaseAssetsDir -File |
        Sort-Object Name |
        ForEach-Object {
            $Hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            "$Hash  $($_.Name)" | Add-Content $ChecksumPath
        }
}

Write-Host "==> Release assets"
Get-ChildItem $ReleaseAssetsDir -File | Sort-Object Name | ForEach-Object {
    $SizeMiB = [math]::Round($_.Length / 1MB, 2)
    Write-Host (" - {0} ({1} MiB)" -f $_.Name, $SizeMiB)
}

Write-Host "==> Done"
Write-Host "Binary: $BinaryPath"
Write-Host "MSI dir: $WixOutputDir"
Write-Host "Bundle: $ReleaseAssetsDir"
