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
