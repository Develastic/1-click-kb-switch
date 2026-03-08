# Windows release guide

## Local release build
1. Install Rust stable, WiX Toolset, and cargo-wix.
2. Run `cargo test --workspace`.
3. Run `cargo build --workspace --release --target x86_64-pc-windows-msvc`.
4. From `/app`, run `cargo wix --package one-click-kb-switch --target x86_64-pc-windows-msvc --output ../target/wix/`.
5. Generate checksums for the MSI and executable.

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
