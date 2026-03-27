import os
import json
import time
import datetime
import logging
import sys
from typing import Any, Callable, List

import httpx
from dbfread import DBF

from agent.windows.sync_config import merged_config

_settings: dict = {}
_logger_configured = False


def _setup_logging() -> None:
    global _logger_configured
    if _logger_configured:
        return
    cfg = merged_config()
    data_dir = cfg.get("data_dir", ".")
    try:
        os.makedirs(data_dir, exist_ok=True)
    except OSError:
        data_dir = "."
    log_path = os.path.join(data_dir, "agent_sync.log")
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)
    if not getattr(sys, "frozen", False):
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        root.addHandler(sh)
    _logger_configured = True


def reload_settings() -> dict:
    global _settings
    _settings = merged_config()
    return _settings


def datetime_convert(v: Any) -> Any:
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    return v


def orden_sort_key(o: str) -> int:
    s = str(o).strip()
    try:
        return int(s)
    except ValueError:
        return 0


def load_checkpoint(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return str(data.get("last_orden", "") or "").strip()
    except (OSError, json.JSONDecodeError):
        return ""


def save_checkpoint(path: str, last_orden: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"last_orden": last_orden, "updated": datetime.datetime.now().isoformat()}, f, indent=2)


def safely_read_dbf(dbc_dir: str, file_name: str, retries: int = 5, delay: int = 5) -> List[dict]:
    path = os.path.join(dbc_dir, file_name)
    if not os.path.exists(path):
        logging.warning("Archivo %s no encontrado en %s", file_name, dbc_dir)
        return []

    for attempt in range(retries):
        try:
            dbf = DBF(path, encoding="latin-1", ignore_missing_memofile=True)
            return [dict(r) for r in dbf]
        except (OSError, PermissionError) as e:
            logging.warning(
                "Archivo %s bloqueado (%s/%s). Reintento en %ss: %s",
                file_name,
                attempt + 1,
                retries,
                delay,
                e,
            )
            time.sleep(delay)

    logging.error("No se pudo leer %s tras %s intentos.", file_name, retries)
    return []


def get_tarjetas_map(dbc_dir: str) -> dict:
    tarjetas_records = safely_read_dbf(dbc_dir, "TARJETAS.DBF")
    tarjeta_map = {}
    for t in tarjetas_records:
        cod = str(t.get("COD_TAR", "")).strip()
        desc = str(t.get("DES_TAR", "")).strip()
        if cod:
            tarjeta_map[cod] = desc
    return tarjeta_map


def process_historical(dbc_dir: str, tarjetas_map: dict, last_orden: str) -> List[dict]:
    factura1 = safely_read_dbf(dbc_dir, "FACTURA1.DBF")
    factura2 = safely_read_dbf(dbc_dir, "FACTURA2.DBF")

    details_map: dict[str, List[dict]] = {}
    for f2item in factura2:
        orden = str(f2item.get("ORDEN", "")).strip()
        if not orden:
            continue
        if f2item.get("GRATIS", 0) == 1:
            continue
        details_map.setdefault(orden, []).append(f2item)

    processed_sales: List[dict] = []
    last_key = orden_sort_key(last_orden) if last_orden else -1

    for f1item in factura1:
        orden = str(f1item.get("ORDEN", "")).strip()
        if not orden:
            logging.warning("FACTURA1 sin ORDEN — se omite (backend registraria huerfano).")
            continue
        if last_key >= 0 and orden_sort_key(orden) <= last_key:
            continue

        if f1item.get("QUE") == 1:
            continue

        codtar = str(f1item.get("CODTAR", "")).strip()
        tipo_tarjeta = tarjetas_map.get(codtar, "Otra/Desconocida") if codtar else "N/A"

        venta_obj = {
            "orden": orden,
            "factura": str(f1item.get("FACTURA", "")).strip(),
            "fecha": datetime_convert(f1item.get("FECHA")),
            "hora": str(f1item.get("HORA1", "")).strip(),
            "total_pagado": float(f1item.get("TOT", 0) or 0),
            "subtotal": float(f1item.get("SUB2", 0) or 0),
            "metodo_pago_tarjeta": tipo_tarjeta,
            "monto_tarjeta": float(f1item.get("TAR", 0) or 0),
            "monto_efectivo": float(f1item.get("EFE", 0) or 0),
            "detalles": [],
        }

        if orden in details_map:
            for d in details_map[orden]:
                venta_obj["detalles"].append(
                    {
                        "codigo": str(d.get("CODIGO", "")).strip(),
                        "cantidad": float(d.get("CANT", 0) or 0),
                        "precio": float(d.get("PRECIO", 0) or 0),
                        "total_renglon": float(d.get("TOTAL", 0) or 0),
                        "descripcion": str(d.get("DESCRIP", "")).strip(),
                    }
                )

        processed_sales.append(venta_obj)

    processed_sales.sort(key=lambda x: orden_sort_key(x["orden"]))
    return processed_sales


def upload_historial(
    rows: List[dict],
    settings: dict,
    on_chunk: Callable[[int, int], None] | None = None,
) -> dict:
    sync_api_url = settings["sync_api_url"].rstrip("/")
    sucursal = settings["sucursal_nombre"].strip()
    pwd = settings.get("sucursal_password") or ""
    api_key = settings.get("sync_api_key") or ""
    batch_size = int(settings.get("batch_size") or 250)

    url = f"{sync_api_url}/sync/upload/{sucursal}"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    if pwd:
        headers["X-Sucursal-Password"] = pwd

    total_new = 0
    errores = 0
    n_chunks = max(1, (len(rows) + batch_size - 1) // batch_size) if rows else 1
    with httpx.Client(timeout=120.0) as client:
        for chunk_num, i in enumerate(range(0, len(rows), batch_size), start=1):
            chunk = rows[i : i + batch_size]
            resp = client.post(url, json={"historial": chunk}, headers=headers)
            resp.raise_for_status()
            body = resp.json()
            total_new += int(body.get("nuevas_ventas_historial_insertadas", 0))
            errores += int(body.get("logs_huerfanos", 0))
            if on_chunk:
                on_chunk(chunk_num, n_chunks)
    return {"nuevas": total_new, "errores": errores}


def _execute_single_sync(progress: Callable[[str, float], None] | None = None) -> dict:
    s = reload_settings()
    dbc = s.get("dbc_dir", r"C:\RestBar\DBC")
    ck = s.get("checkpoint_path") or ""
    suc = s.get("sucursal_nombre", "")
    api = s.get("sync_api_url", "")

    logging.info("Agente sync — sucursal=%s API=%s DBC=%s", suc, api, dbc)
    if not s.get("sucursal_password"):
        logging.warning("sucursal_password vacio. La subida a /sync/upload fallara.")

    if progress:
        progress("Leyendo archivos DBC…", 5.0)

    last = load_checkpoint(ck)
    tarjetas_map = get_tarjetas_map(dbc)
    if progress:
        progress("Procesando ventas pendientes…", 18.0)
    historical_sales = process_historical(dbc, tarjetas_map, last)

    if not historical_sales:
        logging.info("Sin ventas nuevas respecto al checkpoint (o sin datos).")
        if progress:
            progress("Sin ventas nuevas (checkpoint al día, sin DBF o sin datos).", 100.0)
        return {
            "success": True,
            "tickets": 0,
            "nuevas": 0,
            "errores": 0,
            "error": None,
        }

    def on_chunk(cur: int, total: int) -> None:
        if progress:
            pct = 25.0 + 70.0 * (cur / max(total, 1))
            progress(f"Subiendo al servidor: lote {cur} de {total}…", min(pct, 99.0))

    logging.info("Enviando %s tickets nuevos en lotes…", len(historical_sales))
    try:
        summary = upload_historial(historical_sales, s, on_chunk=on_chunk)
    except Exception as e:
        logging.exception("Fallo en sync: %s", e)
        if progress:
            progress(f"Error: {e}", 100.0)
        return {
            "success": False,
            "tickets": len(historical_sales),
            "nuevas": 0,
            "errores": 0,
            "error": str(e),
        }

    max_orden = max(historical_sales, key=lambda x: orden_sort_key(x["orden"]))["orden"]
    save_checkpoint(ck, max_orden)
    logging.info(
        "Sync OK — insertadas ~%s, logs huerfanos=%s, checkpoint ORDEN=%s",
        summary["nuevas"],
        summary["errores"],
        max_orden,
    )
    if progress:
        progress(
            f"Completado: {len(historical_sales)} ticket(s); nuevas ~{summary['nuevas']}, huérfanos {summary['errores']}.",
            100.0,
        )
    return {
        "success": True,
        "tickets": len(historical_sales),
        "nuevas": summary["nuevas"],
        "errores": summary["errores"],
        "error": None,
    }


def run_once() -> None:
    _execute_single_sync(None)


def run_sync_from_gui(progress: Callable[[str, float], None]) -> dict:
    return _execute_single_sync(progress)


def run_sync_agent() -> None:
    s = reload_settings()
    loop = int(s.get("loop_seconds") or 0)
    if loop > 0:
        while True:
            try:
                run_once()
            except Exception as e:
                logging.exception("Error en ciclo de sync: %s", e)
            time.sleep(loop)
    else:
        run_once()


def main() -> None:
    """Arranque: logging, bucle o corrida unica."""
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        if exe_dir and exe_dir not in sys.path:
            sys.path.insert(0, exe_dir)
        root_guess = os.path.dirname(exe_dir)
        if root_guess and root_guess not in sys.path:
            sys.path.insert(0, root_guess)
    _setup_logging()
    reload_settings()
    run_sync_agent()


if __name__ == "__main__":
    main()
