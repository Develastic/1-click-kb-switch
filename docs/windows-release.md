# Windows release guide

## Local build on Linux through Bottles
1. Provision the shared bottle described in `/home/mykola/src/1-click-kb-switch/bottles.md`.
2. Run `./setup.sh`.
3. Run `./build-windows.sh`.
4. The installer appears at `output/windows/1-click-kb-switch-setup.exe`.

## Direct build on Windows
1. Install Python 3.12 with Tk/Tcl support.
2. Install Inno Setup 6.
3. Run `setup.bat`.
4. Run `build-windows.bat`.
5. The installer appears at `output\windows\1-click-kb-switch-setup.exe`.

## GitHub
- GitHub workflow runs are manual only.
- GitHub is used to validate the codebase, not to produce the release installer.
- The canonical Windows release artifact is built locally through Bottles or on a real Windows host.
