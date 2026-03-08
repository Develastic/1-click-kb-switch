# Windows release guide

## Local build
1. Install Python 3.12 with Tk/Tcl support.
2. Install WiX Toolset v3.
3. Run `setup.bat`.
4. Run `build-windows.bat`.

## Outputs
- `dist/release-assets/1-Click-KB-Switch.msi`
- `dist/release-assets/SHA256SUMS.txt`

## Release flow
1. Update `pyproject.toml` version.
2. Push to `main`.
3. Create tag `vX.Y.Z`.
4. GitHub Actions builds and uploads MSI.
