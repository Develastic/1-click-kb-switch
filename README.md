# One Click KB Switch

Cross-platform keyboard layout switcher written in Go.

## Scope
- Targets: Windows amd64, Linux amd64
- CGO: disabled
- Linux support in v1: X11 only
- Wayland: not supported in v1

## Current state
This repository contains the typed application scaffold, config/bootstrap logic,
layout and hotkey logic, platform backend boundaries, tests, and CI.

Important note: truly native cross-platform desktop UI and tray behavior without CGO are
much more constrained than the original feature goal suggests. The current public scaffold
therefore keeps UI and tray integration behind explicit boundaries and does not hide missing
platform capabilities behind silent fallbacks.

Implemented now:
- typed config seeded from embedded `config.json.defaults`
- layout detection logic and label generation
- default binding selection for English / first non-English layout
- `Single Click` detector state machine
- Linux X11 layout discovery through `setxkbmap -query`
- application bootstrap and persistence flow
- test suite and GitHub Actions cross-builds

Not yet implemented at platform level:
- native tray icon/menu
- native global low-level key / mouse hooks
- actual OS layout switching on Windows and Linux
- native graphical settings window

## Run
```bash
./setup.sh
./run-app.sh
```

## Test
```bash
PATH="$HOME/.local/go1.26.1/bin:$PATH" CGO_ENABLED=0 go test ./...
```
