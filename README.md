# One Click KB Switch

Native-first cross-platform keyboard layout switcher.

## Stack
- Rust
- tao for native window/event loop
- tray-icon for tray integration
- global-hotkey for custom global hotkeys
- Linux v1: X11 only
- Windows v1: native layout enumeration, active-layout detection, foreground-window switching, low-level single-click hooks, and MSI packaging pipeline

## Current state
This repository now contains a Windows-oriented native scaffold with:
- typed config creation from embedded defaults
- layout normalization and tray-label generation
- default binding selection for English and first non-English layout
- Windows low-level hook pipeline for `RightCtrl` and `RightShift` single-click detection
- custom combo hotkey capture flow via tray menu + focused window
- tao event loop + tray menu + first-run window behavior
- Linux X11 layout discovery and direct switching through `setxkbmap`
- Windows release metadata, icon, manifest, WiX installer template, and release docs
- unit tests and public CI

## Windows release shape
- Target: `x86_64-pc-windows-msvc`
- Deliverable: MSI installer
- Code signing: intentionally deferred for v1

## Windows native behavior
- First launch shows the window.
- Subsequent launches can start hidden in tray.
- Tray menu exposes layout switching, custom hotkey capture, and settings toggles.
- Low-level single-click switching is implemented for `RightCtrl` and `RightShift`.
- Custom combos are registered through `global-hotkey`.

## Windows local build
On Windows, build the EXE and MSI locally with:
```bat
build-windows.bat
```

Main outputs:
- `target\x86_64-pc-windows-msvc\release\one-click-kb-switch.exe`
- `target\wix\*.msi`
- `target\release-assets\`

## CI and release policy
- Ordinary commits do not trigger GitHub Actions builds.
- Validation runs on pull requests.
- Windows MSI artifacts are built only for manual workflow runs and published releases.

## Versioning policy
- SemVer is used.
- Current public line starts at `0.1.0`.
- Patch (`0.1.x`) is for fixes and installer/runtime corrections.
- Minor (`0.x.0`) is for user-visible features or behavior changes.
- `1.0.0` is reserved for the first Windows release that is manually validated on a real Windows machine.
- Versions should be bumped intentionally for release work, not automatically on every commit.

## Linux native dependencies
Ubuntu/Debian packages required for native build:
- `libgtk-3-dev`
- `libayatana-appindicator3-dev`
- `libxdo-dev`

## Run
```bash
./setup.sh
./run-app.sh
```

## Test
```bash
cargo test --workspace
cargo check --workspace --tests --target x86_64-pc-windows-msvc
```

## Release docs
- `/home/mykola/src/1-click-kb-switch/docs/windows-release.md`
- `/home/mykola/src/1-click-kb-switch/docs/windows-manual-qa.md`
