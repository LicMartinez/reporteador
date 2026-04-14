
# PyInstaller spec — Dashboard Sync SW (watchdog externo).
#   cd REPO_RAIZ
#   pyinstaller agent/windows/DashboardSyncSW-watchdog.spec
import sys
from pathlib import Path

block_cipher = None
SPEC_ROOT = Path(SPECPATH).resolve()
REPO_ROOT = SPEC_ROOT.parent.parent
if str(SPEC_ROOT) not in sys.path:
    sys.path.insert(0, str(SPEC_ROOT))
from pyinstaller_bundles import ucrt_dll_binaries
_ASSETS = REPO_ROOT / 'agent' / 'windows' / 'assets'
_ICO = _ASSETS / 'icono_sincronizador.ico'
if not _ICO.is_file():
    _ICO = _ASSETS / 'app.ico'
icon_path = str(_ICO) if _ICO.is_file() else None

_ucrt_binaries = ucrt_dll_binaries()

a = Analysis(
    [str(SPEC_ROOT / 'watchdog_main.py')],
    pathex=[str(REPO_ROOT)],
    binaries=_ucrt_binaries,
    datas=[],
    hiddenimports=[
        'agent.windows.sync_config',
    ],
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
    name='DashboardSyncSW-watchdog',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
