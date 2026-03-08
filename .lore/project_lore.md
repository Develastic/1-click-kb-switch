# Project Description
1-Click-KB-Switch is a cross-platform desktop keyboard layout switcher for people who use multiple layouts and dislike cyclic switching. The application provides directed switching: one key always maps to one target layout, with single-click modifier bindings such as RightCtrl for English and RightShift for the first non-English layout.

# Project Archirecture
The project uses Python 3.12 with CustomTkinter for the main window and pystray for the tray icon. Domain logic lives in typed dataclass-based core services for config, layouts, hotkeys, and runtime state. Platform-specific behavior is isolated behind a PlatformBackend contract with separate Windows, Linux X11, and experimental Linux Wayland implementations. Windows uses WinAPI integration through ctypes for layout switching and low-level hook processing. Linux X11 uses X11/XKB tooling and python-xlib for event listening. Packaging uses PyInstaller one-dir bundles, WiX-based MSI packaging for Windows, and AppImage packaging for Linux.

# Project Units
- pyproject.toml — project metadata, dependencies, pytest config, console entrypoint.
- config.toml — canonical app metadata and build/runtime constants.
- EULA.md — end-user agreement with no-warranty/no-liability terms.
- app/
  - main.py — thin executable entrypoint.
  - assets/config.json.defaults — default user config template.
  - assets/fonts/dejavusans.ttf — bundled real font for tray label rendering.
  - one_click_kb_switch/
    - app.py — bootstrap entry for RuntimeController and UI.
    - config.py — reads config.toml metadata.
    - paths.py — resolves repo/bundle asset paths.
    - core/models.py — typed dataclasses.
    - core/config.py — AppConfig load/save/defaults/validation.
    - core/layouts.py — english detection, auto labels, default pair selection.
    - core/hotkeys.py — bindings, conflict validation, single-click detector.
    - core/controller.py — runtime orchestration between config, backend, hooks, and UI.
    - platform/base.py — backend contract.
    - platform/factory.py — backend selection by OS/session.
    - platform/windows/backend.py — WinAPI layout switching and low-level hook loop.
    - platform/linux_x11/backend.py — X11 layout handling and record-based event listening.
    - platform/linux_wayland/backend.py — experimental backend with explicit warnings.
    - ui/main_window.py — CustomTkinter main window and tray lifecycle.
    - ui/tray.py — tray menu and font-based icon rendering.
- packaging/windows/installer.wxs — MSI definition with launch-on-exit checkbox.
- packaging/windows/one_click_kb_switch.spec — Windows PyInstaller spec.
- packaging/linux/appimage/one_click_kb_switch.spec — Linux PyInstaller spec.
- docs/windows-release.md — Windows release instructions.
- docs/windows-manual-qa.md — Windows manual QA checklist.
- tests/ — unit tests for config, layouts, and hotkeys.
- .github/workflows/ci.yml — PR validation and manual/tag packaging workflows.

# Notes
- 2026-03-08: Archived the Rust implementation on branch `codex/archive-rust-native-first` before migrating `main` to Python.
- 2026-03-08: Canonical public product name is `1-Click-KB-Switch`; filesystem names stay lowercase.
- 2026-03-08: Tray icon rendering must use a real font to avoid mirrored glyph defects.
- 2026-03-08: MSI installer must offer launching the app after install, opt-out by checkbox.
- 2026-03-08: Wayland is experimental only and must show explicit warnings instead of pretending to support unsupported global hook behavior.
