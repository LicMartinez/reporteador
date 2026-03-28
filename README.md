# SwissTools Pos — Portal dashboard multi-sucursal (MVP)

Backend **FastAPI** + frontend **React (Vite)** + base **PostgreSQL en Supabase**. Ingesta desde puntos de venta vía agente Python de sincronización (opcional en fase inicial).

## Documentación

- **`DEPLOY_MVP.md`** — Retrospectiva, GitHub → Render → Vercel, Supabase, variables de entorno.
- **`docs/VERCEL_DESPLIEGUE.md`** — Cómo publicar el frontend en Vercel (CLI, monorepo, por qué producción puede quedarse en versión vieja).
- **`BUILD_AGENT.md`** — Compilación manual del instalador **Dashboard Sync SW** (PyInstaller + Inno Setup).
- **`docs/AGENTE_WINDOWS.md`** — Uso del agente de sincronización en sucursal.
- **`GUIA_RESTBAR_DASHBOARD.md`** — Dominio DBF, ETL y arquitectura funcional.
- **`1_master_plan_report.md`** — Fases del proyecto.

## Desarrollo local

```powershell
# Backend
cd c:\desarrollo\reporteador
.\venv\Scripts\pip install -r requirements.txt
$env:PYTHONPATH="."
.\venv\Scripts\uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (otra terminal)
cd frontend
npm install
npm run dev
```

## Licencia

Uso interno / según acuerdo del proyecto.
