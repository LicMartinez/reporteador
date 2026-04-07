"""
Configuracion compartida: JSON en ProgramData + overrides por variables de entorno.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

CONFIG_FILENAME = "sync_config.json"

DEFAULT_SYNC_API_URL = "https://reporteador-7qhc.onrender.com"


def program_data_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        return Path(base) / "DashboardSyncSW"
    return Path.home() / ".dashboard_sync_sw"


def default_config_path() -> Path:
    return program_data_dir() / CONFIG_FILENAME


def ensure_data_dir() -> Path:
    d = program_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_config_dict() -> dict:
    return {
        "dbc_dir": r"C:\RestBar\DBC",
        "sucursal_nombre": "",
        "sucursal_password": "",
        "sync_api_url": DEFAULT_SYNC_API_URL.rstrip("/"),
        "sync_api_key": "",
        "loop_seconds": 300,
        "batch_size": 250,
        # Primeras cargas: limitar ventana histórica y/o definir punto de arranque manual.
        "initial_max_months_back": 18,
        "initial_since_date": "",
        "initial_min_orden": "",
        "initial_min_factura": "",
    }


def load_config_file(path: Path | None = None) -> dict:
    p = path or default_config_path()
    if not p.is_file():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _parse_int(value, fallback: int) -> int:
    if value is None or value == "":
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def merged_config() -> dict:
    dfl = default_config_dict()
    file_data = load_config_file()
    out = {**dfl, **file_data}

    if os.environ.get("DBC_DIR"):
        out["dbc_dir"] = os.environ["DBC_DIR"].strip()
    if os.environ.get("SUCURSAL_NOMBRE"):
        out["sucursal_nombre"] = os.environ["SUCURSAL_NOMBRE"].strip()
    if os.environ.get("SUCURSAL_PASSWORD") is not None:
        out["sucursal_password"] = os.environ["SUCURSAL_PASSWORD"].strip()
    if os.environ.get("SYNC_API_URL"):
        out["sync_api_url"] = os.environ["SYNC_API_URL"].rstrip("/").strip()
    if os.environ.get("SYNC_API_KEY") is not None:
        out["sync_api_key"] = os.environ["SYNC_API_KEY"].strip()
    if os.environ.get("SYNC_BATCH_SIZE"):
        out["batch_size"] = _parse_int(os.environ.get("SYNC_BATCH_SIZE"), out["batch_size"])
    if os.environ.get("SYNC_LOOP_SECONDS") is not None:
        out["loop_seconds"] = _parse_int(os.environ.get("SYNC_LOOP_SECONDS"), out["loop_seconds"])
    if os.environ.get("SYNC_INITIAL_MAX_MONTHS_BACK") is not None:
        out["initial_max_months_back"] = _parse_int(
            os.environ.get("SYNC_INITIAL_MAX_MONTHS_BACK"),
            out.get("initial_max_months_back", 18),
        )
    if os.environ.get("SYNC_INITIAL_SINCE_DATE") is not None:
        out["initial_since_date"] = os.environ.get("SYNC_INITIAL_SINCE_DATE", "").strip()
    if os.environ.get("SYNC_INITIAL_MIN_ORDEN") is not None:
        out["initial_min_orden"] = os.environ.get("SYNC_INITIAL_MIN_ORDEN", "").strip()
    if os.environ.get("SYNC_INITIAL_MIN_FACTURA") is not None:
        out["initial_min_factura"] = os.environ.get("SYNC_INITIAL_MIN_FACTURA", "").strip()

    data_dir = ensure_data_dir()
    out["data_dir"] = str(data_dir)

    checkpoint_env = os.environ.get("SYNC_CHECKPOINT_PATH", "").strip()
    if checkpoint_env:
        out["checkpoint_path"] = checkpoint_env
    else:
        cp = file_data.get("checkpoint_path") if isinstance(file_data.get("checkpoint_path"), str) else ""
        out["checkpoint_path"] = (cp.strip() if cp else str(data_dir / "sync_checkpoint.json"))

    return out


def save_config_file(cfg: dict, path: Path | None = None) -> Path:
    p = path or default_config_path()
    ensure_data_dir()
    keys = (
        "dbc_dir",
        "sucursal_nombre",
        "sucursal_password",
        "sync_api_url",
        "sync_api_key",
        "loop_seconds",
        "batch_size",
        "initial_max_months_back",
        "initial_since_date",
        "initial_min_orden",
        "initial_min_factura",
        "checkpoint_path",
    )
    to_write = {k: cfg.get(k) for k in keys}
    if not str(to_write.get("checkpoint_path") or "").strip():
        to_write.pop("checkpoint_path", None)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(to_write, f, indent=2, ensure_ascii=False)
    return p
