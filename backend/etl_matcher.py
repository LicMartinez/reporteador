import collections
import csv
import io
from rapidfuzz import process, fuzz
from . import models

# SIMULACIÓN BASE DE DATOS DE PRODUCTOS DE TODAS LAS SUCURSALES (En la base de datos extraeríamos desde Venta.detalles)
class ETLMatcher:
    def __init__(self, db_session):
        self.db = db_session
        # Tarea 4.2 Mapa Manual (Reglas explícitas de Administrador antes del Fuzz)
        self.manual_map = {
            "BURGER SNG": "Hamburguesa Sencilla",
            "BURG SENCILLA": "Hamburguesa Sencilla",
            "HAMBURGUESA  SENC": "Hamburguesa Sencilla",
            "COCA COLA REG": "Refresco Cola 355ml",
            "COCA. 355": "Refresco Cola 355ml",
            ">PI FRUTOS ROJOS": "Pastel Individual (Varios)"
        }

    def fetch_all_products(self):
        """Tarea 4.3: Extraer productos directamente de los JSON de detalles de Ventas"""
        ventas = self.db.query(models.Venta).all()
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
        """Tarea 4.1: Sistema de emparejamiento string usando agrupaciones por rapidfuzz"""
        raw_products = self.fetch_all_products()
        master_catalog = collections.defaultdict(lambda: {
            "nombres_locales": set(), 
            "cantidad_total": 0, 
            "ingresos_totales": 0.0,
            "sucursales_venta": set()
        })
        
        nombres_unicos_descubiertos = list(set([p["descripcion"] for p in raw_products]))
        
        for p in raw_products:
            desc = p["descripcion"]
            # 1. Chequeo de Mapa Manual (Tarea 4.2 Prioridad 1)
            nombre_maestro = self.manual_map.get(desc)
            
            # 2. IA / Distancia de Levenshtein (RapidFuzz Tarea 4.1)
            if not nombre_maestro:
                # Buscar en las llaves del master dict que ya hemos insertado en vivo
                llaves_maestras = list(master_catalog.keys())
                if llaves_maestras:
                    match = process.extractOne(desc, llaves_maestras, scorer=fuzz.token_sort_ratio)
                    if match and match[1] >= umbral:
                        nombre_maestro = match[0] # Agrupar al máster parecido
                    else:
                        nombre_maestro = desc # Es un producto nuevo/distinto
                else:
                    nombre_maestro = desc
                    
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
