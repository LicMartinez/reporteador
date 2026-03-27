# PyInstaller spec — Dashboard Sync SW (configuracion GUI).
#   cd REPO_RAIZ
#   pyinstaller agent/windows/DashboardSyncSW-config.spec
from pathlib import Path

block_cipher = None
SPEC_ROOT = Path(SPECPATH).resolve()
REPO_ROOT = SPEC_ROOT.parent.parent
_ICO = REPO_ROOT / "agent" / "windows" / "assets" / "app.ico"
icon_path = str(_ICO) if _ICO.is_file() else None

a = Analysis(
    [str(SPEC_ROOT / "config_gui.py")],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=["agent.windows.sync_config"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DashboardSyncSWConfig",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

