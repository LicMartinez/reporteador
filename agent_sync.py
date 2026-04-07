import os
import json
import time
import datetime
import logging
import sys
from typing import Any, Callable, Dict, List

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


def _parse_dbf_date(v: Any) -> datetime.date | None:
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, datetime.date):
        return v
    s = str(v or "").strip()
    if not s:
        return None
    if len(s) >= 10 and s[4:5] == "-" and s[7:8] == "-":
        try:
            return datetime.date.fromisoformat(s[:10])
        except ValueError:
            return None
    return None


def _months_ago(base: datetime.date, months: int) -> datetime.date:
    m = base.month - months
    y = base.year
    while m <= 0:
        m += 12
        y -= 1
    d = min(base.day, [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return datetime.date(y, m, d)


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
    tarjeta_map: dict[str, str] = {}
    for t in tarjetas_records:
        cod = str(t.get("COD_TAR", "")).strip()
        desc = str(t.get("DES_TAR", "")).strip()
        if cod:
            tarjeta_map[cod] = desc
    return tarjeta_map


_MESERO_COD_KEYS = ("COD_MES", "MESERO", "CLAVE", "CODIGO", "NUM_MES", "NUMERO")
_MESERO_NOM_KEYS = ("DES_MES", "NOMBRE", "NOM_MES", "DESCRIP", "DESC", "DES_MESA")


def _first_non_empty_str(row: dict, keys: tuple[str, ...]) -> str:
    for k in keys:
        v = row.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return ""


def get_meseros_map(dbc_dir: str) -> dict:
    rows = safely_read_dbf(dbc_dir, "MESEROS.DBF")
    out: dict[str, str] = {}
    for r in rows:
        cod = _first_non_empty_str(r, _MESERO_COD_KEYS)
        des = _first_non_empty_str(r, _MESERO_NOM_KEYS)
        if cod:
            out[cod] = des
    return out


def lookup_mesero_nombre(meseros_map: dict, cod: str) -> str | None:
    """Resuelve nombre ante códigos con/sin ceros a la izquierda (p. ej. 22 vs 022)."""
    if not cod:
        return None
    if cod in meseros_map:
        n = meseros_map[cod]
        return n if n else None
    alt = cod.lstrip("0") or "0"
    if alt != cod and alt in meseros_map:
        n = meseros_map[alt]
        return n if n else None
    for width in range(2, 6):
        z = cod.zfill(width)
        if z in meseros_map:
            n = meseros_map[z]
            return n if n else None
    return None


def resolve_mesero_codigo(
    f1item: dict,
    details_map: Dict[str, List[dict]],
    orden: str,
) -> str:
    """Encabezado FACTURA1/1T; si viene vacío, primer MESERO en líneas FACTURA2/2T."""
    c = _first_non_empty_str(f1item, ("MESERO", "MAGOS"))
    if c:
        return c
    for d in details_map.get(orden, []):
        c = _first_non_empty_str(d, ("MESERO", "MAGOS"))
        if c:
            return c
    return ""


def _float(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def build_pagos(f1item: dict, tarjetas_map: dict) -> List[dict]:
    """Pares nombre/monto/kind para el dashboard (multi-tarjeta y otros medios)."""
    out: List[dict] = []
    tar_slots = [
        ("CODTAR", "TAR"),
        ("CODTAR2", "TAR2"),
        ("CODTAR3", "TAR3"),
        ("CODTAR4", "TAR4"),
        ("CODTAR5", "TAR5"),
        ("CODTAR6", "TAR6"),
        ("CODTAR7", "TAR7"),
        ("CODTAR8", "TAR8"),
        ("CODTAR9", "TAR9"),
    ]
    for cod_k, amt_k in tar_slots:
        amt = _float(f1item.get(amt_k))
        if amt <= 0:
            continue
        cod = str(f1item.get(cod_k, "")).strip()
        name = tarjetas_map.get(cod, f"Tarjeta {cod or amt_k}") if cod else f"Tarjeta ({amt_k})"
        out.append({"name": name, "amount": amt, "kind": "tarjeta"})

    efe = _float(f1item.get("EFE"))
    if efe > 0:
        out.append({"name": "Efectivo", "amount": efe, "kind": "efectivo"})

    chk = _float(f1item.get("CHK"))
    if chk > 0:
        out.append({"name": "Cheque", "amount": chk, "kind": "otro"})

    vale = _float(f1item.get("VALE"))
    if vale > 0:
        d = str(f1item.get("DVALE", "")).strip()
        out.append({"name": d or "Vale", "amount": vale, "kind": "otro"})

    cup = _float(f1item.get("MON_CUP"))
    if cup > 0:
        out.append({"name": "Cupón / descuento", "amount": cup, "kind": "otro"})

    cre = _float(f1item.get("CRE"))
    if cre > 0:
        d = str(f1item.get("DCRE", "")).strip()
        out.append({"name": d or "Crédito / cuenta", "amount": cre, "kind": "otro"})

    otr = _float(f1item.get("OTR"))
    if otr > 0:
        d = str(f1item.get("DOTR", "")).strip()
        out.append({"name": d or "Otro medio", "amount": otr, "kind": "otro"})

    dol = _float(f1item.get("DOL"))
    if dol > 0:
        out.append({"name": "Dólares (USD)", "amount": dol, "kind": "otro"})

    for label, key in (("Colombianos (COL)", "COL"), ("Colombianos 2 (COL2)", "COL2")):
        v = _float(f1item.get(key))
        if v > 0:
            out.append({"name": label, "amount": v, "kind": "otro"})

    eur = _float(f1item.get("EUR"))
    if eur > 0:
        out.append({"name": "Euros", "amount": eur, "kind": "otro"})

    vip = _float(f1item.get("VIP"))
    if vip > 0:
        out.append({"name": "VIP", "amount": vip, "kind": "otro"})

    return out


def _detalle_line(d: dict) -> dict:
    line = {
        "codigo": str(d.get("CODIGO", "")).strip(),
        "cantidad": float(d.get("CANT", 0) or 0),
        "precio": float(d.get("PRECIO", 0) or 0),
        "total_renglon": float(d.get("TOTAL", 0) or 0),
        "descripcion": str(d.get("DESCRIP", "")).strip(),
    }
    clase_raw = d.get("CLASE")
    try:
        c = int(clase_raw) if clase_raw is not None and str(clase_raw).strip() != "" else 0
    except (TypeError, ValueError):
        c = 0
    if c in (1, 2):
        line["clase"] = c
    cos = d.get("COSVEN")
    if cos is not None:
        try:
            line["costo_renglon"] = float(cos)
        except (TypeError, ValueError):
            pass
    return line


def build_venta_payload(
    f1item: dict,
    details_map: Dict[str, List[dict]],
    tarjetas_map: dict,
    meseros_map: dict,
) -> dict | None:
    orden = str(f1item.get("ORDEN", "")).strip()
    if not orden:
        return None
    if f1item.get("QUE") == 1:
        return None

    pagos = build_pagos(f1item, tarjetas_map)
    monto_tarjeta = sum(p["amount"] for p in pagos if p.get("kind") == "tarjeta")
    monto_efectivo = sum(p["amount"] for p in pagos if p.get("kind") == "efectivo")

    codtar = str(f1item.get("CODTAR", "")).strip()
    tipo_tarjeta = tarjetas_map.get(codtar, "Otra/Desconocida") if codtar else "N/A"

    mesero_cod = resolve_mesero_codigo(f1item, details_map, orden)
    mesero_nombre = lookup_mesero_nombre(meseros_map, mesero_cod) if mesero_cod else None

    detalles: List[dict] = []
    if orden in details_map:
        for d in details_map[orden]:
            if d.get("GRATIS", 0) == 1:
                continue
            detalles.append(_detalle_line(d))

    return {
        "orden": orden,
        "factura": str(f1item.get("FACTURA", "")).strip(),
        "fecha": datetime_convert(f1item.get("FECHA")),
        "hora": str(f1item.get("HORA1", "")).strip(),
        "total_pagado": _float(f1item.get("TOT")),
        "subtotal": _float(f1item.get("SUB2")),
        "metodo_pago_tarjeta": tipo_tarjeta,
        "monto_tarjeta": monto_tarjeta,
        "monto_efectivo": monto_efectivo,
        "pagos": pagos,
        "mesero_codigo": mesero_cod or None,
        "mesero_nombre": mesero_nombre,
        "propinas": _float(f1item.get("TIPS")),
        "detalles": detalles,
    }


def _details_map_from_factura2(rows: List[dict]) -> dict[str, List[dict]]:
    details_map: dict[str, List[dict]] = {}
    for f2item in rows:
        orden = str(f2item.get("ORDEN", "")).strip()
        if not orden:
            continue
        details_map.setdefault(orden, []).append(f2item)
    return details_map


def process_historical(
    dbc_dir: str,
    tarjetas_map: dict,
    meseros_map: dict,
    last_orden: str,
    *,
    initial_max_months_back: int = 18,
    initial_since_date: str = "",
    initial_min_orden: str = "",
    initial_min_factura: str = "",
) -> List[dict]:
    factura1 = safely_read_dbf(dbc_dir, "FACTURA1.DBF")
    factura2 = safely_read_dbf(dbc_dir, "FACTURA2.DBF")
    details_map = _details_map_from_factura2(factura2)

    processed_sales: List[dict] = []
    last_key = orden_sort_key(last_orden) if last_orden else -1
    min_orden_key = orden_sort_key(initial_min_orden) if initial_min_orden else -1
    min_factura_key = orden_sort_key(initial_min_factura) if initial_min_factura else -1
    cutoff_by_months: datetime.date | None = None
    if initial_max_months_back and int(initial_max_months_back) > 0:
        cutoff_by_months = _months_ago(datetime.date.today(), int(initial_max_months_back))
    cutoff_by_date: datetime.date | None = _parse_dbf_date(initial_since_date) if initial_since_date else None
    cutoff_date: datetime.date | None = None
    if cutoff_by_months and cutoff_by_date:
        cutoff_date = max(cutoff_by_months, cutoff_by_date)
    else:
        cutoff_date = cutoff_by_date or cutoff_by_months

    for f1item in factura1:
        orden = str(f1item.get("ORDEN", "")).strip()
        if not orden:
            logging.warning("FACTURA1 sin ORDEN — se omite (backend registraria huerfano).")
            continue
        if last_key >= 0 and orden_sort_key(orden) <= last_key:
            continue
        if last_key < 0:
            if min_orden_key >= 0 and orden_sort_key(orden) < min_orden_key:
                continue
            if min_factura_key >= 0:
                factura = str(f1item.get("FACTURA", "")).strip()
                if orden_sort_key(factura) < min_factura_key:
                    continue
            if cutoff_date is not None:
                fdate = _parse_dbf_date(f1item.get("FECHA"))
                if fdate is not None and fdate < cutoff_date:
                    continue

        venta_obj = build_venta_payload(f1item, details_map, tarjetas_map, meseros_map)
        if venta_obj:
            processed_sales.append(venta_obj)

    processed_sales.sort(key=lambda x: orden_sort_key(x["orden"]))
    return processed_sales


def process_turno_actual(
    dbc_dir: str,
    tarjetas_map: dict,
    meseros_map: dict,
) -> List[dict]:
    """Snapshot completo del turno (FACTURA1T / FACTURA2T)."""
    factura1t = safely_read_dbf(dbc_dir, "FACTURA1T.DBF")
    factura2t = safely_read_dbf(dbc_dir, "FACTURA2T.DBF")
    details_map = _details_map_from_factura2(factura2t)

    out: List[dict] = []
    for f1item in factura1t:
        venta_obj = build_venta_payload(f1item, details_map, tarjetas_map, meseros_map)
        if venta_obj:
            out.append(venta_obj)
    out.sort(key=lambda x: orden_sort_key(x["orden"]))
    return out


def fetch_remote_last_orden(settings: dict) -> str | None:
    """
    Consulta el mayor ORDEN ya guardado en el servidor para esta sucursal.
    Misma autenticación que POST /sync/upload.
    """
    sync_api_url = settings["sync_api_url"].rstrip("/")
    suc = settings["sucursal_nombre"].strip()
    pwd = settings.get("sucursal_password") or ""
    api_key = settings.get("sync_api_key") or ""
    url = f"{sync_api_url}/sync/last-orden/{suc}"
    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key
    if pwd:
        headers["X-Sucursal-Password"] = pwd
    with httpx.Client(timeout=60.0) as client:
        r = client.get(url, headers=headers)
        r.raise_for_status()
        j = r.json()
    lo = j.get("last_orden")
    if lo is None:
        return None
    s = str(lo).strip()
    return s if s else None


def _effective_last_orden_str(local_checkpoint: str, remote_last: str | None) -> str:
    """Mayor ORDEN numérico entre checkpoint local y API (alinear tras fallo o PC nueva)."""
    lk = orden_sort_key(local_checkpoint) if (local_checkpoint or "").strip() else -1
    rk = orden_sort_key(remote_last) if (remote_last or "").strip() else -1
    best = max(lk, rk)
    return str(best) if best >= 0 else ""


def upload_sync(
    historial: List[dict],
    turno_actual: List[dict],
    settings: dict,
    on_chunk: Callable[[int, int], None] | None = None,
    checkpoint_path: str | None = None,
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
    turno_filas = 0

    with httpx.Client(timeout=120.0) as client:
        if not historial:
            body: dict = {"turno_actual": turno_actual}
            resp = client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            b = resp.json()
            total_new += int(b.get("nuevas_ventas_historial_insertadas", 0))
            errores += int(b.get("logs_huerfanos", 0))
            turno_filas += int(b.get("turno_actual_filas", 0))
            return {"nuevas": total_new, "errores": errores, "turno_filas": turno_filas}

        n_chunks = max(1, (len(historial) + batch_size - 1) // batch_size)
        for chunk_num, i in enumerate(range(0, len(historial), batch_size), start=1):
            chunk = historial[i : i + batch_size]
            is_last = i + batch_size >= len(historial)
            body = {"historial": chunk}
            if is_last:
                body["turno_actual"] = turno_actual
            resp = client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            b = resp.json()
            total_new += int(b.get("nuevas_ventas_historial_insertadas", 0))
            errores += int(b.get("logs_huerfanos", 0))
            if is_last:
                turno_filas += int(b.get("turno_actual_filas", 0))
            if checkpoint_path and chunk:
                top = max(chunk, key=lambda x: orden_sort_key(x["orden"]))
                save_checkpoint(checkpoint_path, str(orden_sort_key(top["orden"])))
            if on_chunk:
                on_chunk(chunk_num, n_chunks)

    return {"nuevas": total_new, "errores": errores, "turno_filas": turno_filas}


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

    local_ck = load_checkpoint(ck)
    remote_lo: str | None = None
    try:
        remote_lo = fetch_remote_last_orden(s)
    except Exception as e:
        logging.warning("No se pudo leer /sync/last-orden (se usa solo checkpoint local): %s", e)
    last = _effective_last_orden_str(local_ck, remote_lo)
    if remote_lo or local_ck:
        logging.info(
            "Checkpoint ORDEN: local=%r remoto=%r -> efectivo=%r",
            local_ck or "",
            remote_lo or "",
            last or "(desde inicio)",
        )
    init_months = int(s.get("initial_max_months_back") or 18)
    init_since_date = str(s.get("initial_since_date") or "").strip()
    init_min_orden = str(s.get("initial_min_orden") or "").strip()
    init_min_factura = str(s.get("initial_min_factura") or "").strip()
    if not last:
        logging.info(
            "Carga inicial: max_months_back=%s since_date=%r min_orden=%r min_factura=%r",
            init_months,
            init_since_date,
            init_min_orden,
            init_min_factura,
        )
    tarjetas_map = get_tarjetas_map(dbc)
    meseros_map = get_meseros_map(dbc)
    if progress:
        progress("Procesando turno actual (FACTURA1T)…", 12.0)
    turno_rows = process_turno_actual(dbc, tarjetas_map, meseros_map)
    if progress:
        progress("Procesando ventas históricas pendientes…", 18.0)
    historical_sales = process_historical(
        dbc,
        tarjetas_map,
        meseros_map,
        last,
        initial_max_months_back=init_months,
        initial_since_date=init_since_date,
        initial_min_orden=init_min_orden,
        initial_min_factura=init_min_factura,
    )

    if not historical_sales and not turno_rows:
        logging.info("Sin datos de turno ni histórico nuevo.")
        if progress:
            progress("Sin datos para sincronizar.", 100.0)
        return {
            "success": True,
            "tickets": 0,
            "nuevas": 0,
            "errores": 0,
            "turno_filas": 0,
            "error": None,
        }

    def on_chunk(cur: int, total: int) -> None:
        if progress:
            pct = 25.0 + 70.0 * (cur / max(total, 1))
            progress(f"Subiendo al servidor: lote {cur} de {total}…", min(pct, 99.0))

    logging.info(
        "Enviando sync — histórico: %s ticket(s), turno_actual: %s",
        len(historical_sales),
        len(turno_rows),
    )
    try:
        summary = upload_sync(
            historical_sales,
            turno_rows,
            s,
            on_chunk=on_chunk if historical_sales else None,
            checkpoint_path=ck if ck else None,
        )
    except Exception as e:
        logging.exception("Fallo en sync: %s", e)
        if progress:
            progress(f"Error: {e}", 100.0)
        return {
            "success": False,
            "tickets": len(historical_sales),
            "nuevas": 0,
            "errores": 0,
            "turno_filas": 0,
            "error": str(e),
        }

    logging.info(
        "Sync OK — insertadas histórico ~%s, turno_filas=%s, huérfanos=%s, checkpoint=%s",
        summary["nuevas"],
        summary.get("turno_filas", 0),
        summary["errores"],
        load_checkpoint(ck) or "(sin cambio)",
    )
    if progress:
        progress(
            f"Completado: histórico {len(historical_sales)} ticket(s), turno {len(turno_rows)}; "
            f"nuevas ~{summary['nuevas']}, turno_filas {summary.get('turno_filas', 0)}.",
            100.0,
        )
    return {
        "success": True,
        "tickets": len(historical_sales),
        "nuevas": summary["nuevas"],
        "errores": summary["errores"],
        "turno_filas": summary.get("turno_filas", 0),
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
