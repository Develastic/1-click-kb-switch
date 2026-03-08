# Windows release guide

## Local release build
1. Install Rust stable, WiX Toolset v3, and cargo-wix.
2. Run `build-windows.bat` from the repository root on Windows.
3. Optional flags:
   - `-SkipTests`
   - `-SkipMsi`
   - `-SkipChecksums`
4. The script builds the release EXE, builds the MSI, copies release assets, and generates SHA-256 checksums.

## Output paths
- EXE: `target\x86_64-pc-windows-msvc\release\one-click-kb-switch.exe`
- MSI: `target\wix\*.msi`
- Release bundle: `target\release-assets\`

## Release checklist
- Confirm low-level single-click switching works on a real Windows machine.
- Confirm tray menu actions work after minimize-to-tray.
- Confirm custom combo capture persists to config.
- Confirm installer installs, upgrades, and uninstalls correctly.
- Confirm README, license, and release notes are included in release artifacts.
- Confirm code-signing step is skipped intentionally for v1.

## Future signing
- Add certificate secrets to GitHub Actions.
- Sign the MSI and executable after build, before checksum generation.
- Keep installer shape unchanged so signing remains a pipeline-only addition.
