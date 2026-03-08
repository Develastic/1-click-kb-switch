# One Click KB Switch

Native-first cross-platform keyboard layout switcher.

## Stack
- Rust
- tao for native window/event loop
- tray-icon for tray integration
- global-hotkey for custom global hotkeys
- Linux v1: X11 only
- Windows v1: native layout enumeration, active-layout detection, and foreground-window switching via Win32 APIs

## Current state
This repository contains the Rust-native application skeleton with:
- typed config creation from embedded defaults
- layout normalization and tray-label generation
- default binding selection for English and first non-English layout
- single-click detector state machine
- tao event loop + tray menu + first-run window behavior
- Linux X11 layout discovery and direct switching through `setxkbmap`
- unit tests and public CI

Still explicit work items:
- low-level single-click hooks on both platforms
- full native settings controls inside the tao window
- Windows low-level single-click hooks

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
```
