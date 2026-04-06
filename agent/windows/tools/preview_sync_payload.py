# -*- coding: utf-8 -*-
"""
Vista previa del JSON que enviaría el agente (misma lógica que el ejecutable).
Uso (desde la raíz del repo):
  python agent/windows/tools/preview_sync_payload.py
Opcional: ruta al sync_config.json si no usa ProgramData.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import agent_sync
from agent.windows.sync_config import (
    default_config_dict,
    ensure_data_dir,
    load_config_file,
)


def main() -> None:
    cfg_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if cfg_path:
        raw = load_config_file(cfg_path)
        cfg = {**default_config_dict(), **raw}
        dbc = cfg.get("dbc_dir", "")
        cp = (cfg.get("checkpoint_path") or "").strip() or str(ensure_data_dir() / "sync_checkpoint.json")
        last = agent_sync.load_checkpoint(cp)
    else:
        cfg = agent_sync.reload_settings()
        dbc = cfg.get("dbc_dir", "")
        last = agent_sync.load_checkpoint(cfg.get("checkpoint_path") or "")

    tarjetas = agent_sync.get_tarjetas_map(dbc)
    meseros = agent_sync.get_meseros_map(dbc)
    hist = agent_sync.process_historical(dbc, tarjetas, meseros, last)
    turno = agent_sync.process_turno_actual(dbc, tarjetas, meseros)

    print("dbc_dir:", dbc)
    print("sucursal:", cfg.get("sucursal_nombre"))
    print("histórico pendiente:", len(hist), "ticket(s)  |  turno_actual:", len(turno), "ticket(s)\n")

    if hist:
        print("--- Primer ticket histórico (muestra) ---")
        print(json.dumps(hist[0], indent=2, ensure_ascii=False))
    elif turno:
        print("--- Primer ticket turno_actual (muestra) ---")
        print(json.dumps(turno[0], indent=2, ensure_ascii=False))
    else:
        print("Sin datos: no hay FACTURA1 nuevos respecto al checkpoint ni líneas en FACTURA1T.")


if __name__ == "__main__":
    main()
