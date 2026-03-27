
# PyInstaller spec — Dashboard Sync SW (configuracion GUI).
#   cd REPO_RAIZ
#   pyinstaller agent/windows/DashboardSyncSW-config.spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None
SPEC_ROOT = Path(SPECPATH).resolve()
REPO_ROOT = SPEC_ROOT.parent.parent
_ASSETS = REPO_ROOT / 'agent' / 'windows' / 'assets'
_ICO = _ASSETS / 'icono_sincronizador.ico'
if not _ICO.is_file():
    _ICO = _ASSETS / 'app.ico'
icon_path = str(_ICO) if _ICO.is_file() else None


def _bundle_http():
    datas, binaries, hidden = [], [], []
    for pkg in ('httpx', 'httpcore', 'h11', 'certifi', 'sniffio', 'idna'):
        try:
            d, b, h = collect_all(pkg)
            datas.extend(d)
            binaries.extend(b)
            hidden.extend(h)
        except Exception:
            pass
    return datas, binaries, hidden


_http_datas, _http_binaries, _http_hidden = _bundle_http()

a = Analysis(
    [str(SPEC_ROOT / 'config_gui.py')],
    pathex=[str(REPO_ROOT)],
    binaries=_http_binaries,
    datas=_http_datas,
    hiddenimports=list(
        dict.fromkeys(
            [
                'agent.windows.sync_config',
                'agent_sync',
                'dbfread',
                *_http_hidden,
            ]
        )
    ),
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
    name='DashboardSyncSWConfig',
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
