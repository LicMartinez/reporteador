# Guía técnica — Dashboard multi-sucursal RestBar v19.07A

**Versión del documento:** 1.0  
**Última actualización:** 25 de marzo de 2026  
**Propósito:** Referencia única de dominio (DBF), ETL, sincronización, backend y UI. Sustituye a `restbar_analisis.md` (derivado del análisis DOCX).  
**Roadmap y estatus por fases:** ver `1_master_plan_report.md`. **MVP en producción (visión simple + pasos):** ver `DEPLOY_MVP.md` (Supabase + backend en un host + Vercel; agente y MCP como apéndices).

---

## 1. Visión y alcance

- Consolidar datos de puntos de venta RestBar v19.07A (archivos `.DBF` locales) en un **BI centralizado**, con arquitectura preparada para **muchas sucursales** (objetivo de escala: 50+).
- **MVP piloto:** cuatro sucursales (BAR LOVE, BOCCA, SANA SANA, PANEM). Desde el día 1: **autenticación y permisos por sucursal** (multi-usuario).
- Fuente de datos: típicamente `C:\RestBar\DBC` en cada PC del negocio; el universo completo son **~305 tablas DBF**; para el dashboard solo interesan **unas 13** (el resto es configuración, módulos inactivos o bitácoras).

---

## 2. Arquitectura acordada

| Capa | Rol | Tecnología |
|------|-----|------------|
| Agente (edge) | Lectura DBF, ETL, envío al core; tolerancia a bloqueo de archivos; servicio Windows | Python 3.10, `dbfread`, reintentos (p. ej. 5 s), **NSSM** como servicio |
| Backend (core) | API, persistencia, deduplicación, logs, control de sync, admin | **FastAPI**, **PostgreSQL (Supabase)**, **SQLAlchemy** |
| Frontend | Dashboard, filtros, multi-sucursal | **React**, **Vite**, **TailwindCSS**, **Shadcn/UI**, **Recharts** |

Flujo lógico: **POS (DBF) → Agente → API → Base de datos → Dashboard**.

---

## 3. Conceptos críticos del dominio RestBar

### 3.1 Tablas en vivo vs históricas

| Rol | Tablas | Comportamiento |
|-----|--------|----------------|
| **Turno abierto** | `CUENTAS`, `COMANDAS`, `FACTURA1T`, `FACTURA2T` | Estado actual; `FACTURA*T` se **vacía** en cierre Z y migra al histórico. |
| **Histórico** | `FACTURA1`, `FACTURA2` | Acumulan ventas cerradas; base principal de KPIs y tendencias. |

**Implicación:** el agente debe leer **histórico + turno actual + mesas/comandas en vivo** con **estrategias distintas** (incremental vs reemplazo/upsert).

### 3.2 Ciclo de vida de una venta (resumen)

1. Apertura de mesa → `CUENTAS` (cuenta abierta; `QUE` espacio = abierta).  
2. Pedido → `COMANDAS` (`DSGL=False` hasta enviar a cocina/barra; luego `DSGL=True` en renglones enviados).  
3. Cobro → `FACTURA1T` / `FACTURA2T`; en `CUENTAS` suele reflejarse cobro (`QUE='*'`, `PAG_CTA`, etc.).  
4. Cierre Z → contenido de `FACTURA1T`/`FACTURA2T` pasa a `FACTURA1`/`FACTURA2`; tablas T quedan vacías para el siguiente turno; `CON_REP` registra el cierre (rango de facturas, etc.).

### 3.3 Productos en dos catálogos

En detalle de ventas (`FACTURA2`, y análogo en `COMANDAS`), el campo **`CLASE`** indica el catálogo:

- `CLASE = 1` → artículos (p. ej. `GENERAL.DBF`, campo `COD`).  
- `CLASE = 2` → alimentos (p. ej. `alimento.DBF`, campo `COD_ALI`).

**Alerta:** el **código de producto es local al POS**; el mismo código puede ser otro producto en otra sucursal. Los análisis conglomerado requieren **catálogo maestro** y mapeos por sucursal.

### 3.4 Tarjetas (nombres reales)

`FACTURA1` expone `CODTAR` … `CODTAR9` (y montos asociados). La descripción comercial y comisión vienen de **`TARJETAS.DBF`** (`COD_TAR`, `DES_TAR`, `COM_TAR`, etc.). En reportes hay que hacer **join (LEFT)** por cada slot de tarjeta que se use.

### 3.5 Flags que definen KPIs “limpios”

| Origen | Regla | Efecto en analytics |
|--------|--------|----------------------|
| `FACTURA1.QUE` | `0` = vigente, `1` = anulada | **Filtrar anuladas** en métricas financieras (`QUE = 0`). |
| `FACTURA2.GRATIS` | `1` = cortesía | Excluir de ventas “reales” o marcar `es_cortesia`. |
| `COMANDAS.QUE` | espacio vs `'*'` | Filtrar renglones cancelados en vistas en vivo. |
| `CUENTAS.QUE` | espacio = abierta, `'*'` = cobrada en turno | Filtros para ocupación vs post-cobro. |
| `CUENTAS.DSGL` | `True` = cuenta desglosada / pre-cuenta | Referencia operativa (plan maestro). |

---

## 4. Tablas necesarias para el dashboard (~13)

Encabezado y detalle histórico:

- `FACTURA1.DBF`, `FACTURA2.DBF` — núcleo de ventas cerradas.  
- `FACTURA1T.DBF`, `FACTURA2T.DBF` — mismo esquema (salvo detalles menores); **solo turno actual**. `FACTURA1T` puede incluir campo **`CAJA`** (terminal/caja).  

En vivo:

- `CUENTAS.DBF`, `COMANDAS.DBF`.

Catálogos y soporte:

- `GENERAL.DBF`, `alimento.DBF`, `TARJETAS.DBF`, `CATEGO.DBF`, `MESEROS.DBF`, `CLAVES.DBF`, `AREAS.DBF`, `CON_REP.DBF` (cierres Z), `CONFIG.DBF` / `DIA_CIE.DBF` según necesidad de identidad de sucursal y calendario operativo.

Campos clave habituales (validar siempre contra el DBF real del sitio):

- Join encabezado–detalle: **`FACTURA1.ORDEN = FACTURA2.ORDEN`** (y lo mismo en el par `T`).  
- `CUENTAS.NUM_CTA` enlaza con `COMANDAS.ORDEN`.  
- `COMANDAS.FAKTURA` conecta con el ticket en `FACTURA1T` cuando ya hubo cobro.

---

## 5. Estrategia de sincronización del agente

| Fuente | Frecuencia orientativa | Lectura | Persistencia en backend |
|--------|-------------------------|---------|-------------------------|
| `FACTURA1` + `FACTURA2` | 2–5 min | Incremental desde último checkpoint **con deduplicación robusta** (ver §6) | Filas “histórico” en tablas de hechos |
| `FACTURA1T` + `FACTURA2T` | ~1 min | Conjunto completo del turno (pocas filas) | **Upsert** en tabla(s) dedicadas al turno actual; **no** mezclar con histórico como si fuera definitivo |
| `CUENTAS` | ~30 s | `QUE = ' '` (mesas abiertas) | Upsert + borrar filas que ya no existan en fuente |
| `COMANDAS` | ~30 s | Renglones activos; para cocina/barra suele filtrarse `QUE = ' '` y `DSGL = True` (según producto) | Upsert en tabla en vivo |

**KPI “ventas de hoy”:** puede combinar **histórico del día** (`FACTURA1` con `FECHA = hoy`) **más** **turno en curso** (`FACTURA1T`), evitando doble conteo mediante la lógica de reconciliación cuando un `ORDEN` del turno ya apareció en histórico.

---

## 6. Reglas de integridad y ETL (obligatorias del proyecto)

Estas reglas amplían el análisis de DBF y están alineadas con `1_master_plan_report.md`:

1. **`ORDEN` / `TOT` inválidos:** no detener el agente; registrar en **LOG de errores** en backend y **excluir** de agregados centrales.  
2. **Consecutivos rotos:** no asumir que `ORDEN` es secuencia perfecta; la **unicidad lógica** debe apoyarse en clave compuesta **`FECHA + HORA (de cobro o apertura, según se defina en el modelo) + ORDEN`** además del checkpoint por sucursal.  
3. **Deduplicación:** al detectar en histórico un ticket ya reflejado en tablas de “turno actual”, **eliminar o marcar** la copia temporal para no duplicar métricas.  
4. **Anulaciones y cortesías:** `QUE = 1` en encabezado y `GRATIS = 1` en renglón deben quedar **fuera** de estadísticas financieras o marcados explícitamente.  
5. **Normalización:** `TRIM` en campos texto; fechas “vacías” tipo FoxPro (`1899-12-30`) → `NULL`; horas vacías → `NULL`.  
6. **Catálogos `GENERAL` / `alimento`:** lógica de activo invertida entre tablas (`INACTIVO` vs `ACTIVO`); normalizar a un booleano `activo` coherente.  
7. **Sucursal:** cada registro ingestado debe llevar **identificador de sucursal** acordado (no inferir solo por nombre de carpeta sin convención).

---

## 7. Backend: multi-sucursal, sync y administración

- **Modelo de acceso:** usuarios con relación a sucursales permitidas (p. ej. tablas tipo `USUARIO`, `SUCURSAL`, `USUARIO_SUCURSAL`), además de entidades de negocio (`VENTA`, etc.) y **`LOGS`**.  
- **Control de sincronización:**  
  - `POST /sync/pause` / `POST /sync/resume` — mientras sync pausado, el backend puede rechazar ingesta (p. ej. **503**).  
- **Limpieza:**  
  - `DELETE /admin/limpieza` — borrado por rango y/o reset de checkpoints según política definida.  
- **Ingesta:** el contrato puede ser por lotes JSON (p. ej. `POST /sync/batch` o equivalente en el código actual); mantener idempotencia donde aplique.

Los nombres exactos de tablas SQL y endpoints deben coincidir con el repositorio; esta guía define el **comportamiento esperado**.

---

## 8. Catálogo maestro cross-sucursal

1. Extraer productos únicos por sucursal desde `GENERAL` / `alimento`.  
2. Proponer equivalencias con **`rapidfuzz`** (umbral configurable, p. ej. ~80 %).  
3. **Panel administrativo** para aprobar, corregir o romper mapeos (`codigo_local` + `sucursal` → `id_maestro`).  
4. Reportes conglomerado (Top N, márgenes) deben unir detalle de ventas al **maestro**, no solo al código local.

---

## 9. Frontend (dashboard)

- Autenticación (JWT u mecanismo definido en el proyecto); rutas y datos filtrados por permisos de sucursal.  
- Filtros de tiempo: ayer, hoy, personalizado.  
- Vistas alineadas al negocio: resumen, ventas, productos (idealmente vía maestro), tarjetas con nombres reales, meseros, anulaciones, **vista en vivo** (mesas + turno actual) con refresco periódico.  
- Exportación: Excel/CSV (y PDF si está en alcance), coherente con fase de reportes del plan maestro.

---

## 10. Tablas que normalmente quedan fuera de alcance

Bitácoras masivas, módulos de inventario/delivery/eventos no usados, devoluciones vacías, configuración de teclas, RRHH, compras a proveedores, etc. — salvo que el producto amplíe explícitamente el scope.

---

## 11. Mantenimiento de la documentación

- Cualquier cambio **troncal** (nuevas tablas obligatorias, cambio de reglas ETL, nuevos endpoints de control) debe reflejarse **aquí** y, si aplica, en el checklist de `1_master_plan_report.md`.  
- La fuente histórica del análisis detallado de campos sigue siendo el documento Word **`restbar_analisis_v1.2.docx`** (revisar numeración interna del DOCX si difiere del nombre de archivo).

---

## 12. Referencias cruzadas

| Documento | Uso |
|-----------|-----|
| `1_master_plan_report.md` | Fases, tareas completadas y validaciones del proyecto |
| `restbar_analisis_v1.2.docx` | Análisis extendido de las 305 tablas y listados de campos |
| `GUIA_RESTBAR_DASHBOARD.md` (este archivo) | Guía operativa y de diseño para el equipo |
