from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path.cwd()
a = Analysis(
    [str(root / 'app' / 'main.py')],
    pathex=[str(root / 'app')],
    binaries=[],
    datas=[
        (str(root / 'app' / 'assets' / 'config.json.defaults'), 'assets'),
        (str(root / 'app' / 'assets' / 'fonts' / 'dejavusans.ttf'), 'assets/fonts'),
        (str(root / 'EULA.md'), '.'),
        (str(root / 'LICENSE'), '.'),
        (str(root / 'config.toml'), '.'),
    ],
    hiddenimports=collect_submodules('customtkinter'),
    excludes=['tkinter.test', 'unittest'],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='1-Click-KB-Switch', console=False)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name='1-Click-KB-Switch')
