# Plan Maestro de Implementación: Dashboard Multi-Sucursal RestBar v19.07A
**Versión:** 1.2
**Fecha de Creación:** 25 de marzo de 2026
**Estatus Actual:** Inicialización

## 🌟 1. Visión General
Desarrollar un ecosistema de inteligencia de negocios centralizado en tiempo real, diseñado para escalar y soportar de forma nativa a **más de 50 sucursales a futuro**. La meta principal es consolidar los datos de cualquier punto de venta RestBar v19.07A centralizando las métricas y superando las limitaciones de los archivos `.DBF` locales.
**Nota MVP:** Durante la primera etapa piloto (MVP) el desarrollo priorizará pruebas con 4 sucursales iniciales (BAR LOVE, BOCCA, SANA SANA, PANEM), pero la arquitectura base y el sistema de acceso mediante usuarios **(Autenticación y Permisos por Sucursal)** regirán desde el día 1.

## 🛡️ 2. Directrices de Integridad y Robustez (Protocolos Anti-Errores)
El sistema en diseño mitigará fallos operativos comunes en RestBar mediante las siguientes reglas fundamentales:

| Directriz | Descripción Técnica y Control |
| :--- | :--- |
| **Gestión de Datos Huérfanos/Vacíos** | Todas las variables vitales (`ORDEN`, `TOT`) deben ser íntegras. Ante un campo `ORDEN` vacío o corrompido, el Agente no interrumpe el proceso, lo traslada a un **LOG de Errores** del Backend y lo aísla de los KPIs centrales. |
| **Consecutivos Rotos** | La sincronización no asume secuencias perfectas. Usará la clave compuesta de `FECHA + HORA + ORDEN` para catalogar unicidad, librando así bloqueos frente a los saltos en folios (`ORDEN`). |
| **Limpieza (ETL) y Anulaciones** | Los registros donde `QUE = 1` o `GRATIS = 1` se marcan como inactivos/anulados y quedan fuera de las estadísticas financieras. `DSGL = True` define las mesas que ya pidieron cuenta (`CUENTAS.DBF`). |

## 🛠️ 3. Arquitectura del Sistema
*   **Agente (Edge - Sincronizador):** En Python 3.10 gestionando pausas por concurrencia usando `dbfread`. Corre bajo Windows (instala como Servicio usando NSSM).
*   **Backend (Core):** API centralizada con FastAPI + Bases de Datos en PostgreSQL (Supabase) manejada mediante el ORM SQLAlchemy.
*   **Frontend (UI):** React + TailwindCSS + Shadcn/UI + Recharts.

## 🚀 4. Fases de Ejecución (Roadmap y Estatus)

### 🟢 Fase 0: Inicialización y Entorno (COMPLETADA)
- [x] `setup_environment`: Instalación de FastAPI, DBFRead, SQLAlchemy, etc.
- [x] `test_dbf_connection`: Validaciones de lectura `latin-1` directas en los DBF reales exitosas. Probamos folios vacíos.

### 🟢 Fase 1: Extracción Segura (Agente Python) - *Completada*
**Objetivo:** Agente seguro para lectura incremental bajo manejo pasivo de bloqueos de archivo.
- [x] Tarea 1.1: Script de lectura incremental cruzando `CUENTAS` (mesas vivas) y `FACTURA1/2` (histórico).
- [x] Tarea 1.2: Lógica de reconexión/re-intento. Si RestBar tiene bloqueado el archivo, esperar de manera asíncrona (5s).
- [x] Tarea 1.3: `deploy_agent_service`. Generación e instalación del servicio para Windows.
- [x] **Validación:** Extracción de datos huérfanos prevenida, script exportando output JSON maestro para backend.

### 🟢 Fase 2: Backend y Control de Flujo (Core API) - *Completada*
**Objetivo:** Estructurar el almacenamiento, reglas de acceso multi-usuario, flujos de recepción, y consola de administración.
- [x] Tarea 2.1: Modelado Multi-Inquilino (Multi-Tenant) y Autenticación en SQL. Tablas `USUARIO`, `SUCURSAL`, `USUARIO_SUCURSAL` (Permisos), `VENTA`, `LOGS`.
- [x] Tarea 2.2: Generar endpoints Pausa/Reanudación de Sync: `POST /sync/pause`, `POST /sync/resume`.
- [x] Tarea 2.3: Generación de Endpoint de Limpieza `DELETE /admin/limpieza` (Borrado por Rango y reseteos completos de Checkpoint).
- [x] Tarea 2.4: Lógica interna de Deduplicación.
- [x] **Validación:** Pausar endpoint, lanzar peticiones y ratificar los errores 503 HTTP de rechazo por pausa.

### 🟢 Fase 3: Dashboard MVP (Interfaces) - *Completada*
**Objetivo:** Explotación de la información visual de altas métricas, con intuitividad, filtros de tiempo (Ayer, Hoy, Personalizado), y control multi-sucursal rápido.
- [x] Tarea 3.1: Configuración de Entorno React, Vite y dependencias TailwindCSS y Lucide-React.
- [x] Tarea 3.2: Estructura del "Glassmorphism" Layout, Selectores Globales y Grid de KPIs dinámicos.
- [x] Tarea 3.3: Integración de Gráficas Recharts (Área para ingresos por hora y Barras para formas de pago).
- [x] **Validación:** Renderizado correcto de interfaz en modo desarrollo sin dependencias rotas.

### 🟢 Fase 4: Inteligencia y Catálogo Maestro (ETL e IDs Globales) - *Completada*
**Objetivo:** Emparejamiento e inteligencia artificial de productos en un catálogo homologado.
- [x] Tarea 4.1: Sistema de emparejamiento string usando agrupaciones por `rapidfuzz` de los IDs locales entre POS.
- [x] Tarea 4.2: Panel administrativo para ajustar mapas manuales ("Burger Sng" -> "Hamburguesa Sencilla").
- [x] Tarea 4.3: Exportables y reportes finales por Excel/CSV.
- [x] **Validación:** Top 10 Platillos a nivel conglomerado consolidando las 4 sucursales juntas.

---
*Nota Diaria: Cada modificación troncal de estructura o fase completada deberá actualizar el estatus de las tareas listadas en este documento.*
