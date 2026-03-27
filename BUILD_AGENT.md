# Build manual: Dashboard Sync SW (agente Windows)

Todo el proceso lo ejecutas en tu PC; **no** hay CI automático para el instalador.

## Requisitos

- Windows x64
- Python 3.12+ (recomendado)
- [Inno Setup 6](https://jrsoftware.org/isdl.php) (opcional: `compiler:Languages\Spanish.isl` para asistente en español)
- Origen del icono: `agent/windows/assets/icono_sincronizador.png`

## 1. Entorno Python

Desde la **raíz del repo** `reporteador`:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-agent-build.txt
```

## 2. Generar `app.ico` (si cambias el PNG)

```powershell
python agent/windows/tools/png_to_ico.py
```

Salida: `agent/windows/assets/app.ico`

## 3. PyInstaller

Desde la raíz del repo:

```powershell
pyinstaller agent/windows/DashboardSyncSW-worker.spec --noconfirm
pyinstaller agent/windows/DashboardSyncSW-config.spec --noconfirm
```

Salida: `dist/DashboardSyncSW.exe` (consola, bucle de sync) y `dist/DashboardSyncSWConfig.exe` (GUI).

## 4. Inno Setup

1. Abrir `agent/windows/DashboardSyncSW.iss` en Inno Setup Compiler.
2. **Build → Compile**.
3. Instalador: `output_installer/DashboardSyncSW-Setup-1.0.0.exe` (cambia `#define MyAppVersion` en el `.iss` si subes versión).

Antes de compilar, verifica que existan los dos `.exe` en `dist/` y `agent/windows/assets/app.ico`.

## Servicio Windows (opcional)

Usa [NSSM](https://nssm.cc/) u otra herramienta apuntando a `DashboardSyncSW.exe` en la carpeta de instalación. La cuenta del servicio debe poder **leer** la carpeta DBC del POS. El intervalo del bucle está en `sync_config.json` (`loop_seconds`).

Consulta también [docs/AGENTE_WINDOWS.md](docs/AGENTE_WINDOWS.md).
