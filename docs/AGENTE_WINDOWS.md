# Dashboard Sync SW — operación en sucursal

## Qué hace el agente

- Lee archivos **DBF** en la carpeta configurada (por defecto `C:\RestBar\DBC`): `FACTURA1.DBF`, `FACTURA2.DBF`, `TARJETAS.DBF`.
- Envía ventas nuevas al **API** (`POST /sync/upload/{nombre_sucursal}`) con la contraseña de sincronización (`X-Sucursal-Password`).
- **No** conecta a Supabase ni usa `DATABASE_URL`. El servidor (p. ej. Render) es quien escribe en Postgres.

## Configuración

1. Instalar con el instalador generado por Inno Setup o usar los `.exe` de `dist/`.
2. Ejecutar **Dashboard Sync SW** (configuración) desde el menú Inicio.
3. Completar:
   - **Carpeta DBC** del POS.
   - **Nombre sucursal**: exactamente igual que en Swiss Admin (`sucursales.nombre`).
   - **Contraseña de sync**: la definida al crear la sucursal en el portal administrativo.
   - **URL del API**: la de producción o la que corresponda.

Archivos en el equipo:

| Ruta | Uso |
|------|-----|
| `C:\ProgramData\DashboardSyncSW\sync_config.json` | Configuración |
| `C:\ProgramData\DashboardSyncSW\agent_sync.log` | Log del worker |
| `C:\ProgramData\DashboardSyncSW\sync_checkpoint.json` | Último ORDEN enviado (por defecto) |

## Bucle

- **Intervalo > 0**: el proceso repite cada N segundos (servicio o tarea programada).
- **Intervalo = 0**: una sola corrida (pruebas).

## Checklist en el portal administrativo

- Crear la sucursal con el **mismo nombre** y **contraseña de sync** que en el agente.
- Asignar sucursales (y catálogo si aplica) a cada usuario del dashboard.

Instrucciones de compilación: [BUILD_AGENT.md](../BUILD_AGENT.md).

---

## Roadmap: icono en bandeja del sistema (próxima versión)

Hoy el agente corre **sin ventana** (`DashboardSyncSW.exe` compilado con `console=False`); el usuario lo ve en el **Administrador de tareas**. Una mejora natural es un **icono en el área de notificación** (bandeja junto al reloj) con menú contextual (p. ej. *Abrir configuración*, *Salir del agente*).

### Requisitos técnicos en Windows

Un icono de bandeja (`Shell_NotifyIcon`) necesita:

1. Un **HWND** (ventana oculta mínima suele bastar) asociado al proceso.
2. Un **bucle de mensajes** (`GetMessage` / `DispatchMessage`) en el hilo que recibe eventos del icono (clics, menú).

El worker actual solo ejecuta el bucle de sincronización en Python; **no** tiene bomba de mensajes Win32. Por tanto hay que **combinar** el sync con un bucle de UI de bandeja en el mismo proceso (o dividir en dos procesos comunicados).

### Enfoques recomendados (orden sugerido)

#### 1. **pystray** (recomendado para prototipo)

- Biblioteca multiplataforma; en Windows usa ctypes contra `shell32` / `user32`.
- Patrón habitual: hilo secundario con la lógica de sync (`agent_sync.run_sync_agent()` o el bucle actual) y **hilo principal** bloqueado en `pystray.Icon.run()` (o al revés según la documentación de la versión usada: a veces el icono debe ir en el hilo principal).
- **Icono**: `PIL.Image` o ruta a `.ico`; alinear con `agent/windows/assets/icono_sincronizador.ico`.
- **PyInstaller**: añadir `pystray` (y `Pillow` si se usa imagen en memoria) a `hiddenimports` o `collect_all` en el `.spec` del worker; probar en máquina limpia.
- **Menú**: `pystray.Menu` con entradas que lancen `DashboardSyncSWConfig.exe` (`subprocess.Popen`) y otra que termine el proceso del agente de forma ordenada.

Ventaja: poco código Win32 explícito. Desventaja: dependencia extra y acierto del modelo de hilos con el bucle de sync.

#### 2. **WinAPI directa (ctypes)** o **pywin32**

- Implementar `RegisterClass`, `CreateWindow` (ventana oculta), `Shell_NotifyIcon`, y el bucle de mensajes en C/Python.
- Máximo control y sin `pystray`, pero más código y mantenimiento.

#### 3. **Proceso dedicado solo a bandeja**

- Un ejecutable mínimo que solo muestra el icono y arranca o vigila `DashboardSyncSW.exe`.
- Más archivos y coordinación (mutex, pipes, etc.); útil si se quiere mantener el worker absolutamente sin UI.

### Qué tocar en el repositorio (cuando se implemente)

| Área | Cambios típicos |
|------|------------------|
| [`agent/windows/worker_main.py`](../agent/windows/worker_main.py) | Tras el mutex de instancia única, iniciar bandeja + delegar sync a un hilo (o invertir según librería). |
| [`agent_sync.py`](../agent_sync.py) | Posible refactor para que `run_sync_agent()` sea invocable desde un hilo sin asumir consola; logging ya es a archivo en frozen. |
| Dependencias | Añadir `pystray` y, si aplica, `Pillow` a un requirements de agente o a `requirements-agent-runtime.txt`. |
| [`agent/windows/DashboardSyncSW-worker.spec`](../agent/windows/DashboardSyncSW-worker.spec) | Incluir módulos/datos ocultos para pystray/PIL; volver a probar `console=False`. |
| Inno Setup | Sin cambios obligatorios si solo se enriquece el mismo `DashboardSyncSW.exe`. |

### Comportamiento UX sugerido

- **Clic** en el icono: abrir `DashboardSyncSWConfig.exe` (misma carpeta de instalación).
- **Menú contextual**: *Configuración*, *Abrir carpeta de datos* (`%ProgramData%\DashboardSyncSW`), *Salir* (termina solo el proceso del agente con bandeja; dejar claro que deja de sincronizar hasta el próximo arranque o tarea programada).
- Opcional: tooltip con estado (*Sincronizando…*, *Última corrida: …*) leyendo log o un archivo de estado pequeño.

### Pruebas

- Windows 10/11, iconos ocultos vs visibles en la bandeja (configuración “Mostrar icono”).
- Instalación con Inno + reinicio de sesión.
- Un solo mutex de instancia: no duplicar iconos si el usuario ejecuta el instalador dos veces o hay tarea programada + arranque manual.

Este apartado es **solo referencia** para la siguiente versión; la versión actual sigue sin icono de bandeja a propósito para reducir complejidad y dependencias.
