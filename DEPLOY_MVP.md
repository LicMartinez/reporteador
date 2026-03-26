# MVP: retrospectiva y despliegue simple

## Retrospectiva — por qué se sintió “engorroso”

La idea original era clara: **datos en Supabase** y **interfaz en Vercel**. Conforme avanzamos el MVP se fueron sumando piezas legítimas pero **distintas de cara al socio**:

| Capa real | Para el desarrollador | Para “solo dos plataformas” |
|-----------|------------------------|-----------------------------|
| **PostgreSQL** | Supabase | Sí — es la base de datos. |
| **API FastAPI** | Tiene que ejecutarse **en algún servidor** (no vive dentro del build estático de Vercel). | Suele presentarse como *“el backend”*; Render/Railway/Fly son solo **proveedores** del mismo proceso Python. |
| **Frontend React** | Vercel | Sí. |
| **Agente + .exe + NSSM** | Sucursales Windows | Es **ingesta de datos**, no parte del “dashboard web” para la demo inicial. |
| **MCP (Cursor)** | Comodidad de desarrollo | No forma parte del producto ni del despliegue MVP. |

**Conclusión:** no hay que eliminar la API Python para ser simple; hay que **simplificar el relato** y la documentación:

1. **Hacia afuera (socios):** “La app está en **Vercel**; los datos en **Supabase**.”
2. **Hacia dentro (tú):** la API es un **único servicio** con URL pública; elige **un** hosting (p. ej. Render) y no lo expliques como “otra plataforma del producto”, sino como *donde corre el backend*.
3. **Demo sin cajas:** puedes cargar datos de prueba con SQL o un script contra Supabase y **posponer** agente + .exe a cuando el MVP ya esté validado.

---

## Stack mínimo para el primer MVP funcional

```
[Vercel]  ──HTTPS──►  [Backend FastAPI en un host]  ──►  [Supabase Postgres]
   │                           ▲
   │                           │  (más adelante: agente en cada PC)
   └── login + dashboard       POST /sync/upload
```

Variables que importan:

| Dónde | Variables |
|-------|-----------|
| **Host del backend** | `DATABASE_URL` (Supabase), `JWT_SECRET`, `ALLOWED_ORIGINS`, opcional `SYNC_API_KEY` |
| **Vercel (frontend)** | `VITE_API_URL` = URL pública del backend, sin `/` final |

---

## 0. Repositorio en GitHub y enlace con Render

Render despliega desde **Git** (GitHub, GitLab o Bitbucket). El flujo habitual es:

### A) Crear el repositorio en GitHub

1. Entra en [github.com/new](https://github.com/new).
2. **Repository name:** por ejemplo `reporteador` (o el que prefieras).
3. **Público** o **Privado** (Render funciona con ambos si conectas la cuenta).
4. **No marques** “Add a README” si ya tienes código local y vas a hacer `push` por primera vez (evita conflictos).
5. Crea el repositorio y copia la URL **HTTPS**, p. ej. `https://github.com/TU_USUARIO/reporteador.git`.

### B) Subir este proyecto desde tu PC (PowerShell)

En la carpeta del proyecto (ya con `git init` y primer commit si lo generamos en el repo):

```powershell
cd c:\desarrollo\reporteador
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

Si GitHub pide autenticación, usa un **Personal Access Token** (classic o fine-grained con permiso `repo`) en lugar de la contraseña, o el **GitHub CLI** (`gh auth login`).

### C) Conectar Render al mismo repositorio

1. [Render Dashboard](https://dashboard.render.com) → **New** → **Web Service**.
2. **Connect account** → autoriza **GitHub** y elige el repositorio `reporteador` (o el nombre que hayas puesto).
3. **Branch:** `main`.
4. **Root directory:** vacío (raíz del repo, donde está `requirements.txt`).
5. **Build:** `pip install -r requirements.txt`  
6. **Start:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
7. Añade las variables de entorno (`DATABASE_URL`, `JWT_SECRET`, `ALLOWED_ORIGINS`, etc.) y despliega.

Cada `git push` a `main` puede activar **auto-deploy** si lo habilitas en el servicio (Settings → Auto-Deploy).

### D) Vercel con el mismo repo

En Vercel → Add New Project → importa el **mismo** repositorio; **Root Directory** = `frontend` y variable `VITE_API_URL` apuntando a la URL que te dio Render.

> **Nota:** `.cursor/mcp.json` está en `.gitignore` para no subir tokens. La plantilla sin secretos es `.cursor/mcp.json.example`.

---

## 1. Base de datos — Supabase (ya preparada)

Proyecto **restbar-reporteador-mvp** · ref `rnxzksljzqjwxzjaaqay` · migración `initial_restbar_schema`.

- SQL versionado: `supabase/migrations/20260325233443_initial_restbar_schema.sql`
- **Connection string:** [Project → Settings → Database](https://supabase.com/dashboard/project/rnxzksljzqjwxzjaaqay/settings/database) (pooler recomendado para servidor).

---

## 2. Backend — un solo servicio Python (ejemplo: Render)

Vercel sirve el **frontend estático/SSR**; la **API** sigue siendo este repo (`uvicorn backend.main:app`).

1. **New → Web Service** (o Blueprint con `render.yaml` en la raíz).
2. **Build:** `pip install -r requirements.txt`  
3. **Start:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. **Environment:** `DATABASE_URL`, `JWT_SECRET`, `ALLOWED_ORIGINS` (origen de tu URL de Vercel + `http://localhost:5173` si desarrollas local).  
   - Si usas sync desde agente: misma `SYNC_API_KEY` aquí y en las PCs.

**Alternativas al mismo rol:** Railway, Fly.io, Google Cloud Run, etc. — mismo código, misma env.

**Seed del primer usuario admin** (desde tu PC, misma `DATABASE_URL` que el servidor):

```powershell
cd c:\desarrollo\reporteador
$env:PYTHONPATH="."
$env:DATABASE_URL="postgresql+psycopg2://..."   # la de Supabase
$env:SEED_ADMIN_EMAIL="socio@tuempresa.com"
$env:SEED_ADMIN_PASSWORD="UnaClaveSegura"
.\venv\Scripts\python scripts\seed_admin.py
```

Comprueba: `GET https://tu-api.../` → `{"status":"ok",...}`.

---

## 3. Frontend — Vercel

1. Proyecto con **root directory** `frontend`.
2. `VITE_API_URL=https://tu-api.onrender.com` (o la URL que sea).
3. Deploy. Rutas SPA: `frontend/vercel.json`.

---

## Apéndice A — Agente de sincronización (cuando toque producción en cajas)

No es necesario para demostrar **login + dashboard + datos de prueba**. Cuando quieras datos reales desde RestBar:

- `build_agent.bat` → carpeta `dist\RestBarSyncAgent\`
- Variables: `DBC_DIR`, `SUCURSAL_NOMBRE`, `SYNC_API_URL`, `SYNC_API_KEY`, etc. (detalle en código `agent_sync.py`).

---

## Apéndice B — MCP (Cursor)

Herramientas de desarrollo; **no** las cuentes como plataforma del MVP frente a socios.

---

## Apéndice C — Endpoints útiles

- `POST /auth/login` · `GET /auth/me` · `GET /dashboard/resumen?...`  
- `POST /sync/upload/{SUCURSAL}` + `X-API-Key` si configuraste `SYNC_API_KEY`

---

## Seguridad

No subas `.env`, tokens `sbp_...`, `JWT_SECRET` ni `SYNC_API_KEY` al repositorio. Usa variables de entorno en el host del backend y en Vercel.
