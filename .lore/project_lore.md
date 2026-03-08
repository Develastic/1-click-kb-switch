# Project Description
One Click KB Switch is a native-first cross-platform desktop keyboard layout switcher. The project now targets Rust instead of Go, focuses on Windows amd64 and Linux amd64, uses tao for the native event loop/window shell, tray-icon for tray integration, and keeps user configuration in OS-specific config directories.

# Project Archirecture
The application uses a Rust workspace with a native desktop app crate under app/. Typed serde models own config, layouts, and hotkeys. Platform-specific behavior is isolated behind a PlatformBackend trait with Linux X11 and Windows implementations. The app uses tao for the event loop and main window shell, tray-icon for tray menu/icon handling, a pure-Rust bitmap glyph generator for dynamic two-letter tray icons, and Windows low-level hooks for single-click detection. Linux v1 uses X11 tooling and does not support Wayland. Windows releases are packaged as MSI installers via WiX.

# Project Units
- Cargo.toml — workspace manifest.
- app/
  - Cargo.toml — application crate manifest and native dependencies.
  - build.rs — Windows resource embedding.
  - assets/config.json.defaults — embedded default user config template.
  - assets/app.ico — Windows icon for executable and installer metadata.
  - src/main.rs — bootstrap entry point.
  - src/lib.rs — crate module exports.
  - src/config.rs — typed config model, defaults embedding, OS path resolution, load/save/create methods.
  - src/layouts.rs — layout normalization, english detection, tray-label generation.
  - src/hotkeys.rs — hotkey model, default bindings, validation, combo conversion, single-click detector state machine.
  - src/runtime.rs — typed runtime state for active layout, hooks, tray, and capture mode.
  - src/sound.rs — runtime switch sound behavior.
  - src/platform/mod.rs — backend trait and platform factory.
  - src/platform/linux_x11.rs — Linux X11 layout discovery and switching via setxkbmap.
  - src/platform/windows.rs — Windows layout enumeration, active-layout detection, and switching via Win32 APIs.
  - src/platform/windows_hooks.rs — Windows low-level keyboard and mouse hook thread for single-click detection.
  - src/state.rs — bootstrap orchestration, defaults selection, warnings, runtime state updates, custom binding persistence.
  - src/tray.rs — tray menu, tray command mapping, two-letter icon generation.
  - src/ui.rs — tao event loop, tray/window lifecycle, combo registration, capture flow, active-layout refresh loop.
  - windows/app.manifest — Windows executable manifest.
  - wix/main.wxs — WiX installer definition.
- docs/
  - windows-release.md — Windows release procedure.
  - windows-manual-qa.md — Windows manual acceptance checklist.
- .github/workflows/ci.yml — CI plus Windows release packaging job.
- .github/release/windows-release-notes-template.md — release notes template.
- setup.sh/setup.bat — Rust toolchain bootstrap helpers.
- run-app.sh/run-app.bat — run helpers.
- README.md — public project documentation and current limitations.
- LICENSE — MIT license.

# Notes
- 2026-03-08: Removed the Go scaffold and replaced it with a Rust native-first workspace.
- 2026-03-08: Chosen stack: tao + tray-icon + global-hotkey-oriented architecture.
- 2026-03-08: Linux v1 remains X11-only; Wayland is explicitly unsupported.
- 2026-03-08: Windows layout enumeration, active-layout detection, and foreground-window switching are wired through Win32 APIs.
- 2026-03-08: Added Windows low-level keyboard/mouse hook runtime for single-click detection, tray-driven custom hotkey capture, MSI packaging template, icon, manifest, and Windows release documentation.
- 2026-03-08: No silent fallbacks were introduced for unsupported platform capabilities.
- 2026-03-08: Added local Windows build scripts for EXE/MSI generation, release-asset bundling, and checksum generation.
