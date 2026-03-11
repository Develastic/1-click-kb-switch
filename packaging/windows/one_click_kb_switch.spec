from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path.cwd()
block_cipher = None

a = Analysis(
    [str(root / 'app' / 'main.py')],
    pathex=[str(root / 'app')],
    binaries=[],
    datas=[
        (str(root / 'app' / 'assets' / 'config.json.defaults'), 'assets'),
        (str(root / 'app' / 'assets' / 'fonts' / 'dejavusans.ttf'), 'assets/fonts'),
        (str(root / 'app' / 'assets' / 'sounds' / 'switch-click.wav'), 'assets/sounds'),
        (str(root / 'app' / 'assets' / 'sounds' / 'credits.txt'), 'assets/sounds'),
        (str(root / 'EULA.md'), '.'),
        (str(root / 'LICENSE'), '.'),
        (str(root / 'config.toml'), '.'),
    ],
    hiddenimports=collect_submodules('customtkinter'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter.test', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='1-click-kb-switch', console=False)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name='1-click-kb-switch')
