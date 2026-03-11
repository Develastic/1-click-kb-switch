# Bottles Windows build environment

Shared Windows build environment for Ubuntu that uses **Bottles + Flatpak + a single shared win64 bottle** and keeps Python isolation at the **per-project `uv` virtual environment** layer.

## What this repository provides

- One canonical bottle: `win-build-main`
- One canonical Bottles storage path: `/home/mykola/.var/app/com.usebottles.bottles/data/bottles/bottles/win-build-main`
- Windows-side `uv.exe` at: `C:\tools\uv\uv.exe`
- Windows installer cache at: `C:\installers`
- Inno Setup compiler at: `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`
- A sample validation project at `/home/mykola/sysadmin/bottles/examples/hello-pyinstaller`

## Host prerequisites

- Ubuntu with `flatpak`
- Network access for Bottles, uv, CPython, and Microsoft installers
- Enough disk space for one shared bottle and Windows toolchain downloads

## Provision the environment

From `/home/mykola/sysadmin/bottles` run:

```bash
./setup.sh
```

What `setup.sh` does:

1. installs Bottles from Flathub if missing;
2. grants Flatpak filesystem access to `/home/mykola`;
3. creates the shared custom `win64` bottle `win-build-main`;
4. copies Windows `uv.exe` into `C:\tools\uv`;
5. stages Microsoft installer bootstrap executables into `C:\installers`;
6. runs `vc_redist.x64.exe` silently;
7. runs Visual Studio Build Tools with the VCTools workload and recommended components;
8. installs Inno Setup silently and verifies `ISCC.exe`.

## Canonical host wrappers

### Open an interactive Windows command prompt

```bash
./open-bottle-cmd.sh
```

### Run an arbitrary Windows command in the shared bottle

```bash
./run-bottle-cmd.sh 'C:\tools\uv\uv.exe --version'
```

### Run a Windows command from a host project directory

```bash
./run-project-cmd.sh /absolute/host/project 'C:\tools\uv\uv.exe python install 3.12'
```

The project directory is entered inside Wine as a `Z:` path, for example:

- host path: `/home/mykola/src/myapp`
- Windows path inside the bottle: `Z:\home\mykola\src\myapp`


### Compile an Inno Setup script

```bash
./run-inno.sh /absolute/path/to/installer.iss
```

Example for the included sample project:

```bash
./run-inno.sh /home/mykola/sysadmin/bottles/examples/hello-pyinstaller/installer.iss
```

## Canonical project build flow

Do **not** build directly from the `Z:`-mounted host workspace.
For reliable `uv` locking and faster packaging, copy the project into a staging directory on the bottle's internal `C:` drive and build there.

Recommended flow inside the bottle:

```cmd
robocopy Z:\path\to\project C:\build\project-stage /MIR
cd /d C:\build\project-stage
C:\tools\uv\uv.exe python install 3.12
C:\tools\uv\uv.exe venv .venv-windows --python 3.12
set UV_PROJECT_ENVIRONMENT=.venv-windows
set UV_LINK_MODE=copy
set UV_CACHE_DIR=C:\uv-cache\project-name
C:\tools\uv\uv.exe sync --python 3.12 --link-mode copy
.venv-windows\Scripts\python.exe -m unittest discover -s tests -v
.venv-windows\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath dist-windows --workpath build-windows your.spec
```

Rules:

- the bottle is shared by all projects;
- every project creates its own Windows `.venv` inside the bottle staging folder;
- there is no global project venv in the bottle;
- Python versions are installed on demand with `uv`;
- build/test/package steps should run from the bottle's internal `C:` disk, not from the host-mounted `Z:` tree;
- project-specific SDK or packaging quirks belong in that project's own build documentation.

## Verify the environment

Run the included validation build:

```bash
./test-build.sh
```

The validation project uses `uv sync --no-install-project --link-mode copy` because it is only a dependency fixture, it does not ship an installable package, and staging on `C:` is more reliable than building directly on Wine `Z:` mounts.

Expected artifacts:

- `/home/mykola/sysadmin/bottles/examples/hello-pyinstaller/dist/hello-cli.exe`
- `/home/mykola/sysadmin/bottles/examples/hello-pyinstaller/output/hello-cli-setup.exe` after running Inno Setup

## Operational notes

- This bottle is intentionally **custom** and **non-gaming**: `DXVK`, `VKD3D`, `NVAPI`, and `LatencyFleX` are disabled.
- Bottles CLI forces offline mode for component discovery, so this repository creates the bottle through Bottles' internal Python API while keeping the runner/tooling explicit and reproducible.
- Current implementation uses the runner that Bottles exposes locally during provisioning. On this host that is the Flatpak-managed `sys-wine-11.0` runner.

## Known warnings on this host

Current validation on this Ubuntu host succeeds, but two warnings may still be visible during command execution:

- `winemenubuilder.exe -a -r` may print on command startup; the bottle still runs and builds successfully.
- `uv` may print `Failed to unlock resource ... Lock violation` when it touches Wine/Z-drive mounted paths. The preferred mitigation is to stage sources, caches, venv, tests, and packaging work under `C:\build\...` and only copy final artifacts back to the host.

## Installer packaging for releases

Use **Inno Setup** as the default release installer for packages that will later be submitted to `winget`. `winget` accepts `exe` installers, so MSI is not required for this environment.
