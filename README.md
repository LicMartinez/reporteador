# RestBar — Dashboard multi-sucursal (MVP)

Backend **FastAPI** + frontend **React (Vite)** + base **PostgreSQL en Supabase**. Ingesta desde puntos de venta RestBar vía agente Python (opcional en fase inicial).

## Documentación

- **`DEPLOY_MVP.md`** — Retrospectiva, GitHub → Render → Vercel, Supabase, variables de entorno.
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
