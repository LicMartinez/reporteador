# Build manual: Dashboard Sync SW (agente Windows)

Todo el proceso lo ejecutas en tu PC; **no** hay CI automático para el instalador.

## Requisitos

- Windows x64
- Python 3.12+ (recomendado)
- [Inno Setup 6](https://jrsoftware.org/isdl.php) (opcional: `compiler:Languages\Spanish.isl` para asistente en español)
- Icono de compilación: `agent/windows/assets/icono_sincronizador.ico` (o `icono_sincronizador.png` + script Pillow).

## 1. Entorno Python

Desde la **raíz del repo** `reporteador`:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-agent-build.txt
```

`requirements-agent-build.txt` ya incluye `httpx`, `dbfread` y PyInstaller; evita instalar todo `requirements.txt` (útil si `psycopg2-binary` u otras dependencias del backend fallan en tu versión de Python). Para desarrollar el API en la misma máquina, instala aparte `requirements.txt`.

## 2. Icono para PyInstaller e Inno

Opción A (recomendada): coloca **`agent/windows/assets/icono_sincronizador.ico`** (tu archivo listo para compilar).

Opción B: generar desde el PNG con Pillow:

```powershell
python agent/windows/tools/png_to_ico.py
```

Salida por defecto: `agent/windows/assets/app.ico` (los `.spec` usan primero `icono_sincronizador.ico`, si no existe `app.ico`).

## 3. Prueba antes de PyInstaller / Inno (opcional)

Con dependencias instaladas (`requirements.txt`), desde la raíz del repo:

```powershell
$env:PYTHONPATH="."
python agent/windows/tools/smoke_test.py
```

Debe terminar con `OK - smoke test terminado.` y mensajes `INFO`/`WARNING` esperables si no hay DBF (usa temporales; no toca tu `ProgramData` real).

Para probar la GUI en fuente:

```powershell
$env:PYTHONPATH="."
python agent/windows/config_gui.py
```

## 4. PyInstaller

Desde la raíz del repo:

```powershell
pyinstaller agent/windows/DashboardSyncSW-worker.spec --noconfirm
pyinstaller agent/windows/DashboardSyncSW-config.spec --noconfirm
```

Salida: `dist/DashboardSyncSW.exe` (consola, bucle de sync) y `dist/DashboardSyncSWConfig.exe` (GUI).

Los `.spec` empaquetan la pila HTTP y tienen **UPX desactivado**, lo que suele reducir falsos positivos de antivirus. Los `.exe` sin firma pueden ser bloqueados: permitir en el dispositivo, reportar falso positivo o firmar con Authenticode.

## 5. Inno Setup

1. Abrir `agent/windows/DashboardSyncSW.iss` en Inno Setup Compiler.
2. **Build → Compile**.
3. Instalador: `output_installer/DashboardSyncSW-Setup-1.3.0.exe` (cambia `#define MyAppVersion` en el `.iss` si subes versión).

Antes de compilar, verifica que existan los dos `.exe` en `dist/` y `agent/windows/assets/icono_sincronizador.ico` (o `app.ico` como respaldo).

## Servicio Windows (opcional)

Usa [NSSM](https://nssm.cc/) u otra herramienta apuntando a `DashboardSyncSW.exe` en la carpeta de instalación. La cuenta del servicio debe poder **leer** la carpeta DBC del POS. El intervalo del bucle está en `sync_config.json` (`loop_seconds`).

Consulta también [docs/AGENTE_WINDOWS.md](docs/AGENTE_WINDOWS.md) (incluye un **roadmap** para icono en bandeja del sistema en una versión futura).
