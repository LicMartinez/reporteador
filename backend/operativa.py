"""
Día operativo (corte por sucursal): ventas entre medianoche y la hora de corte
cuentan como el día comercial anterior, alineado con turnos nocturnos.

Regla universal simplificada (v2):
  Si la hora del ticket es < CORTE (default 06:00 = 360 min), la fecha de negocio
  es el día calendario anterior. Esto se calcula al momento del sync y se persiste
  en la columna `fecha_operacion`.

Compatibilidad: se mantiene `hora_corte_operativa_minutos` por sucursal para
permitir cortes personalizados. Si es NULL se usa el DEFAULT_CORTE_MINUTOS (360 = 06:00).
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

_HORA_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})")

# Corte por defecto: 06:00 AM (360 minutos desde medianoche)
DEFAULT_CORTE_MINUTOS = 360


def parse_hora_to_minutes(hora: Optional[str]) -> int:
    """Minutos desde medianoche 0..1439; hora inválida o vacía => 0."""
    if not hora or not str(hora).strip():
        return 0
    m = _HORA_RE.match(str(hora).strip())
    if not m:
        return 0
    hh = int(m.group(1))
    mm = int(m.group(2))
    if hh > 23 or mm > 59:
        return 0
    return min(1439, hh * 60 + mm)


def fecha_operativa_iso(fecha: Optional[str], hora: Optional[str], corte_minutos: Optional[int]) -> str:
    """
    Fecha comercial YYYY-MM-DD para un ticket con fecha/hora POS.
    Si corte_minutos es None se usa DEFAULT_CORTE_MINUTOS (06:00).
    Regla: hora < corte → fecha de negocio = día anterior.
    """
    raw = (fecha or "").strip()[:10]
    if len(raw) != 10:
        return ""
    try:
        d = date.fromisoformat(raw)
    except ValueError:
        return raw
    corte = corte_minutos if corte_minutos is not None else DEFAULT_CORTE_MINUTOS
    hm = parse_hora_to_minutes(hora)
    if hm < corte:
        d = d - timedelta(days=1)
    return d.isoformat()


def calcular_fecha_operacion(fecha: Optional[str], hora: Optional[str], corte_minutos: Optional[int] = None) -> str:
    """
    Calcula la fecha de negocio para persistir en `fecha_operacion`.
    Usa corte_minutos de la sucursal o DEFAULT_CORTE_MINUTOS si es None.
    """
    return fecha_operativa_iso(fecha, hora, corte_minutos)


def widen_iso_range(fecha_desde: str, fecha_hasta: str) -> tuple[str, str]:
    """Amplía el rango calendario ±1 día para capturar tickets madrugada del día operativo."""
    d0 = date.fromisoformat(fecha_desde[:10])
    d1 = date.fromisoformat(fecha_hasta[:10])
    return (d0 - timedelta(days=1)).isoformat(), (d1 + timedelta(days=1)).isoformat()


def venta_en_rango_operativo(
    fecha: Optional[str],
    hora: Optional[str],
    sucursal_id: str,
    fecha_desde: str,
    fecha_hasta: str,
    cutoff_map: dict[str, Optional[int]],
) -> bool:
    corte = cutoff_map.get(str(sucursal_id))
    op = fecha_operativa_iso(fecha, hora, corte)
    return bool(op) and fecha_desde <= op <= fecha_hasta


def sql_fecha_operativa_expr(alias: str, join_alias: str) -> str:
    """
    Expresión SQL (Postgres) que devuelve fecha operativa como texto YYYY-MM-DD.
    `alias` = tabla ventas o ventas_turno (v / t); `join_alias` = sucursales (s / s_t).
    Usa hora_corte_operativa_minutos de la sucursal; si es NULL usa DEFAULT (360 = 06:00).
    """
    hora_col = f"{alias}.hora"
    fecha_col = f"{alias}.fecha"
    corte_col = f"{join_alias}.hora_corte_operativa_minutos"
    return f"""(
  CASE WHEN COALESCE(
    CASE WHEN (regexp_match(trim(COALESCE({hora_col},'')), '^([0-9]{{1,2}}):([0-9]{{2}})')) IS NOT NULL THEN
      ((regexp_match(trim(COALESCE({hora_col},'')), '^([0-9]{{1,2}}):([0-9]{{2}})'))[1])::int * 60
      + ((regexp_match(trim(COALESCE({hora_col},'')), '^([0-9]{{1,2}}):([0-9]{{2}})'))[2])::int
    END, 0
  ) < COALESCE({corte_col}, {DEFAULT_CORTE_MINUTOS}) THEN ({fecha_col}::date - INTERVAL '1 day')::date::text
  ELSE {fecha_col} END
)"""


def sql_fecha_operacion_column_expr() -> str:
    """
    Expresión SQL simplificada que usa la columna pre-calculada `fecha_operacion`.
    Fallback a `fecha` si `fecha_operacion` es NULL (datos legacy sin backfill).
    """
    return "COALESCE(NULLIF(fecha_operacion, ''), fecha)"
