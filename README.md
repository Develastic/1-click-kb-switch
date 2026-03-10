# 1-Click-KB-Switch

**1-Click-KB-Switch** is a desktop utility for people who use multiple keyboard layouts and are tired of traditional cyclic switchers.

With a cyclic switcher, a hotkey only means “go to the next layout”, so you still have to remember where you are now. **1-Click-KB-Switch** provides **directed switching**: one key always means one target layout. Press `RightCtrl` and you know you will get English. Press `RightShift` and you know you will get your first non-English layout. For frequently used layouts, the fastest method is a single click on a modifier key.

## Stack
- Python 3.12
- CustomTkinter
- Native platform backends
- Windows x64: supported
- Linux X11 x64: supported
- Linux Wayland: experimental

## Identity
- Canonical name: **1-Click-KB-Switch**
- Company: **Develastic**
- Company URL: [https://develastic.com](https://develastic.com)
- Author: **Mykola Rudenko**

## Current functionality
- User config is created from `app/assets/config.json.defaults`
- First launch opens the main window
- Subsequent launches start hidden in tray
- Tray menu is intentionally minimal: `Show main window`, `Exit`
- Default directed bindings:
  - `LeftCtrl` → first detected English layout
  - `LeftShift` → first detected non-English layout
- Custom bindings can be assigned per layout
- Tray labels are rendered with a real font to avoid mirrored glyph issues
- Linux tray menu uses the AppIndicator backend, not the limited XOrg fallback
- Windows MSI installer includes an optional “Launch 1-Click-KB-Switch” checkbox

## Install and run for development
```bash
./setup.sh
./run-app.sh
```

On Windows:
```bat
setup.bat
run-app.bat
```

## Local packaging
Windows:
```bat
build-windows.bat
```

Linux:
```bash
./build-linux.sh
```

## Release policy
- Ordinary commits do not trigger release builds
- Pull requests run validation
- Manual workflow builds test artifacts
- Tags in the form `vX.Y.Z` publish release artifacts
- The version tag must match `pyproject.toml`

## License and agreement
- License: MIT
- End-user agreement: `/home/mykola/src/1-click-kb-switch/EULA.md`
