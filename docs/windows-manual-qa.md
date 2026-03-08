# Windows manual QA

## Runtime validation
- First launch shows the main window.
- Second launch starts hidden in tray.
- `RightCtrl` single-click switches to English layout.
- `RightShift` single-click switches to first non-English layout.
- Holding a target key and pressing another key cancels switching.
- Mouse click between key down/up cancels switching.
- Tray label matches the active layout after switching.
- `Show main window` and `Exit` work from tray.

## Custom hotkey validation
- Start capture from tray menu.
- Focused window shows capture mode in the title.
- Press a combo such as `Ctrl + Alt + Q`.
- Captured combo is persisted and re-registered.
- Clearing a custom hotkey removes it from runtime state and config.

## Installer validation
- MSI installs without manual file moves.
- App icon and version metadata appear in Windows shell.
- Uninstall entry is created.
- Uninstall removes binaries and shortcuts.
