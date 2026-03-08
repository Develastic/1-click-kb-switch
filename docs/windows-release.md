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

## GitHub release flow
1. Update `app/Cargo.toml` to the target release version, for example `0.1.1`.
2. Push the version commit to `main`.
3. In GitHub, open **Releases**.
4. Click **Draft a new release**.
5. Create a new tag in the form `vX.Y.Z`, for example `v0.1.1`, from branch `main`.
6. Publish the release.
7. The `ci` workflow starts on the tag push, builds the Windows EXE and MSI, and uploads them to the same GitHub release.
8. Download the MSI from the release assets and run manual QA on a real Windows machine.

## Manual test build from GitHub Actions
1. Open **Actions**.
2. Select the `ci` workflow.
3. Click **Run workflow**.
4. Choose branch `main`.
5. Start the workflow.
6. Download the `windows-release-bundle` artifact from the completed run.
7. Use that MSI for non-release Windows testing.

## Future signing
- Add certificate secrets to GitHub Actions.
- Sign the MSI and executable after build, before checksum generation.
- Keep installer shape unchanged so signing remains a pipeline-only addition.
