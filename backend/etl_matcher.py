import collections
import csv
import io
from rapidfuzz import process, fuzz
from typing import Optional

from . import models

class ETLMatcher:
    def __init__(
        self,
        db_session,
        catalogo_maestro_id: Optional[str] = None,
        sucursal_ids: Optional[list[str]] = None,
        umbral: int = 85,
    ):
        self.db = db_session
        self.catalogo_maestro_id = catalogo_maestro_id
        self.sucursal_ids = sucursal_ids
        self.umbral = umbral

        # Reglas del catálogo maestro: alias_local -> nombre_maestro
        self.alias_to_maestro: dict[str, str] = {}
        self.alias_list: list[str] = []
        if catalogo_maestro_id:
            rules = (
                self.db.query(models.CatalogoMaestroProducto)
                .filter(models.CatalogoMaestroProducto.catalogo_id == catalogo_maestro_id)
                .all()
            )
            self.alias_list = [r.alias_local for r in rules]
            self.alias_to_maestro = {r.alias_local: r.nombre_maestro for r in rules}

    def fetch_all_products(self):
        """Extrae productos desde `Venta.detalles` (JSON) para mapearlos a nombres maestros."""
        query = self.db.query(models.Venta)
        if self.sucursal_ids:
            query = query.filter(models.Venta.sucursal_id.in_(self.sucursal_ids))
        ventas = query.all()
        productos = []
        for v in ventas:
            for item in getattr(v, "detalles", []):
                desc = item.get("descripcion", "").upper().strip()
                if not desc: continue
                # Limpieza base ETL
                desc = desc.replace("++", "").replace(">", "").strip()
                productos.append({
                    "sucursal": v.sucursal.nombre if v.sucursal else "Desconocida",
                    "codigo_local": item.get("codigo"),
                    "descripcion": desc,
                    "cantidad": item.get("cantidad", 0),
                    "total": item.get("total_renglon", 0)
                })
        return productos

    def group_and_match(self, umbral=85):
        """Mapea descripciones locales a nombres maestros usando el catálogo (alias + fuzzy)."""
        umbral = umbral or self.umbral
        raw_products = self.fetch_all_products()
        master_catalog = collections.defaultdict(
            lambda: {
                "nombres_locales": set(),
                "cantidad_total": 0,
                "ingresos_totales": 0.0,
                "sucursales_venta": set(),
            }
        )

        for p in raw_products:
            desc_norm = str(p["descripcion"]).upper().strip()

            nombre_maestro = None
            if self.alias_to_maestro and desc_norm in self.alias_to_maestro:
                # Coincidencia exacta por alias (prioridad 1)
                nombre_maestro = self.alias_to_maestro[desc_norm]

            if not nombre_maestro and self.alias_list:
                # Coincidencia fuzzy contra alias del catálogo
                match = process.extractOne(desc_norm, self.alias_list, scorer=fuzz.token_sort_ratio)
                if match and match[1] >= umbral:
                    best_alias = match[0]
                    nombre_maestro = self.alias_to_maestro.get(best_alias)

            if not nombre_maestro:
                # Fallback si no hay reglas: usa la descripción local como “maestro”
                nombre_maestro = p["descripcion"]
                    
            # Acumulador Inteligente Consolidador
            node = master_catalog[nombre_maestro]
            node["nombres_locales"].add(desc)
            node["cantidad_total"] += p["cantidad"]
            node["ingresos_totales"] += p["total"]
            node["sucursales_venta"].add(p["sucursal"])
            
        return master_catalog
    
    def export_top10_to_csv(self):
        """Tarea 4.3: Exportables y Reportes (Top 10 Consolidado)"""
        master_catalog = self.group_and_match()
        
        # Sort by Quantity (Top Sold) or Total Income
        sorted_catalog = sorted(
            master_catalog.items(), 
            key=lambda x: x[1]["cantidad_total"], 
            reverse=True
        )[:10] # Top 10 Platos
        
        # Create CSV in Memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Platillo_Maestro", "Alias_Locales", "Sucursales_Involucradas", "Qty_Vendida", "Ingresos_Totales_Neto"])
        
        for k, v in sorted_catalog:
            writer.writerow([
                k,
                " | ".join(v["nombres_locales"]),
                " | ".join(v["sucursales_venta"]),
                round(v["cantidad_total"], 2),
                round(v["ingresos_totales"], 2)
            ])
            
        return output.getvalue()
