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
pyinstaller agent/windows/DashboardSyncSW-watchdog.spec --noconfirm
```

Salida: `dist/DashboardSyncSW.exe` (worker), `dist/DashboardSyncSWConfig.exe` (GUI) y `dist/DashboardSyncSW-watchdog.exe` (watchdog).

Los `.spec` empaquetan la pila HTTP y tienen **UPX desactivado**, lo que suele reducir falsos positivos de antivirus. Los `.exe` sin firma pueden ser bloqueados: permitir en el dispositivo, reportar falso positivo o firmar con Authenticode.

### Windows 8.1 / 7: `api-ms-win-crt-runtime-l1-1-0.dll` no encontrada

Ese DLL forma parte del **Universal C Runtime (UCRT)**. No es un fallo del instalador en sí, sino del sistema sin ese runtime.

**Opción A — Solo en el equipo cliente (sin “actualizar Windows” al completo)**  
Instalar el paquete independiente de Microsoft (no sustituye a Service Pack ni sube de versión el SO):

- Busca en el sitio de Microsoft: **“Visual C++ Redistributable for Visual Studio 2015-2022”** (elige **x64**; el agente se compila en 64 bits).
- Ejecuta `VC_redist.x64.exe` y reinicia si el instalador lo pide.

Eso instala las DLL UCRT que PyInstaller/Python necesitan. No equivale a instalar feature updates de Windows 10/11.

**Opción B — Incluir UCRT dentro del .exe al compilar (recomendado para repartir sin requisitos extra)**  
En la **máquina donde compilas** debe existir el **Windows 10/11 SDK** (p. ej. con Visual Studio: componente “Windows SDK” o SDK standalone). Los `.spec` llaman a `agent/windows/pyinstaller_bundles.py`, que copia las DLL UCRT oficiales del SDK al binario onefile. Vuelve a ejecutar PyInstaller + Inno; el cliente en Windows 8.1 no debería pedir ese DLL.

Si al compilar no tienes SDK, `ucrt_dll_binaries()` devuelve lista vacía y el comportamiento es el de siempre (hace falta Opción A en el cliente).

## 5. Inno Setup

1. Abrir `agent/windows/DashboardSyncSW.iss` en Inno Setup Compiler.
2. **Build → Compile**.
3. Instalador: `output_installer/DashboardSyncSW-Setup-1.4.0.exe` (cambia `#define MyAppVersion` en el `.iss` si subes versión).

Antes de compilar, verifica que existan los dos `.exe` en `dist/` y `agent/windows/assets/icono_sincronizador.ico` (o `app.ico` como respaldo).

## Servicio Windows + watchdog (recomendado en producción)

1. Crea el servicio (NSSM u otra herramienta) apuntando a `DashboardSyncSW.exe`.
2. Mantén el nombre de servicio como `DashboardSyncSW` (o define `worker_service_name` en `sync_config.json`).
3. Activa watchdog externo (`worker_watchdog_enabled: true`).
4. El watchdog usa `agent_heartbeat.json` para detectar estado stale; si el proceso sigue vivo pero deja de actualizar heartbeat, forzará reinicio del servicio.

Claves nuevas en `sync_config.json`:

- `heartbeat_path`: ruta del heartbeat (default `C:\\ProgramData\\DashboardSyncSW\\agent_heartbeat.json`)
- `worker_service_name`: nombre del servicio Windows
- `worker_watchdog_enabled`: habilita watchdog externo
- `worker_watchdog_interval_seconds`: intervalo de revisión del watchdog
- `worker_stale_threshold_seconds`: umbral para considerar colgado al worker

En modo fuente (`python`), también puedes ejecutar watchdog manualmente:

```powershell
$env:PYTHONPATH="."
python agent/windows/watchdog_main.py
```

Consulta también [docs/AGENTE_WINDOWS.md](docs/AGENTE_WINDOWS.md) (incluye un **roadmap** para icono en bandeja del sistema en una versión futura).
