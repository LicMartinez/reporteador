import os
import json
import time
import datetime
import logging
from typing import Any, List

import httpx
from dbfread import DBF

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("agent_sync_error.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

DBC_DIR = os.environ.get("DBC_DIR", r"C:\RestBar\DBC")
SUCURSAL_NOMBRE = os.environ.get("SUCURSAL_NOMBRE", "SUC_PRUEBA").strip()
SYNC_API_URL = os.environ.get("SYNC_API_URL", "http://127.0.0.1:8000").rstrip("/")
SYNC_API_KEY = os.environ.get("SYNC_API_KEY", "").strip()
CHECKPOINT_PATH = os.environ.get("SYNC_CHECKPOINT_PATH", "sync_checkpoint.json")
BATCH_SIZE = int(os.environ.get("SYNC_BATCH_SIZE", "250"))
LOOP_SECONDS = int(os.environ.get("SYNC_LOOP_SECONDS", "0"))


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


def load_checkpoint() -> str:
    if not os.path.isfile(CHECKPOINT_PATH):
        return ""
    try:
        with open(CHECKPOINT_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return str(data.get("last_orden", "") or "").strip()
    except (OSError, json.JSONDecodeError):
        return ""


def save_checkpoint(last_orden: str) -> None:
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump({"last_orden": last_orden, "updated": datetime.datetime.now().isoformat()}, f, indent=2)


def safely_read_dbf(file_name: str, retries: int = 5, delay: int = 5) -> List[dict]:
    path = os.path.join(DBC_DIR, file_name)
    if not os.path.exists(path):
        logging.warning("Archivo %s no encontrado en %s", file_name, DBC_DIR)
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


def get_tarjetas_map() -> dict:
    tarjetas_records = safely_read_dbf("TARJETAS.DBF")
    tarjeta_map = {}
    for t in tarjetas_records:
        cod = str(t.get("COD_TAR", "")).strip()
        desc = str(t.get("DES_TAR", "")).strip()
        if cod:
            tarjeta_map[cod] = desc
    return tarjeta_map


def process_historical(tarjetas_map: dict, last_orden: str) -> List[dict]:
    factura1 = safely_read_dbf("FACTURA1.DBF")
    factura2 = safely_read_dbf("FACTURA2.DBF")

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
            logging.warning("FACTURA1 sin ORDEN — se omite (backend registraría huérfano).")
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


def upload_historial(rows: List[dict]) -> dict:
    url = f"{SYNC_API_URL}/sync/upload/{SUCURSAL_NOMBRE}"
    headers = {"Content-Type": "application/json"}
    if SYNC_API_KEY:
        headers["X-API-Key"] = SYNC_API_KEY

    total_new = 0
    errores = 0
    with httpx.Client(timeout=120.0) as client:
        for i in range(0, len(rows), BATCH_SIZE):
            chunk = rows[i : i + BATCH_SIZE]
            resp = client.post(url, json={"historial": chunk}, headers=headers)
            resp.raise_for_status()
            body = resp.json()
            total_new += int(body.get("nuevas_ventas_historial_insertadas", 0))
            errores += int(body.get("logs_huerfanos", 0))
    return {"nuevas": total_new, "errores": errores}


def run_once() -> None:
    logging.info("Agente sync — sucursal=%s API=%s", SUCURSAL_NOMBRE, SYNC_API_URL)
    last = load_checkpoint()
    tarjetas_map = get_tarjetas_map()
    historical_sales = process_historical(tarjetas_map, last)

    if not historical_sales:
        logging.info("Sin ventas nuevas respecto al checkpoint (o sin datos).")
        return

    logging.info("Enviando %s tickets nuevos en lotes de %s...", len(historical_sales), BATCH_SIZE)
    summary = upload_historial(historical_sales)
    max_orden = max(historical_sales, key=lambda x: orden_sort_key(x["orden"]))["orden"]
    save_checkpoint(max_orden)
    logging.info(
        "Sync OK — insertadas ~%s, logs huérfanos=%s, checkpoint ORDEN=%s",
        summary["nuevas"],
        summary["errores"],
        max_orden,
    )


def run_sync_agent() -> None:
    if LOOP_SECONDS > 0:
        while True:
            try:
                run_once()
            except Exception as e:
                logging.exception("Error en ciclo de sync: %s", e)
            time.sleep(LOOP_SECONDS)
    else:
        run_once()


if __name__ == "__main__":
    run_sync_agent()
