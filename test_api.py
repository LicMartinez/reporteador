from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.deps import get_current_user
from backend.main import app


def _fake_maintenance_user():
    return SimpleNamespace(
        id="test-maintenance",
        portal_admin=True,
        is_admin=True,
        email="test@local",
        nombre=None,
    )


app.dependency_overrides[get_current_user] = _fake_maintenance_user
client = TestClient(app)

def test_flujos_fase2():
    print("Iniciando Pruebas Unitarias. Backend Core Local...")
    
    # 1. Crear Venta Simulación (Deduplicación Tarea 2.4 / Tarea 2.1)
    payload = {
        "historial": [
            {
                "orden": "101",
                "factura": "T01",
                "fecha": "2026-03-24",
                "hora": "12:00",
                "total_pagado": 100,
                "subtotal": 85,
                "metodo_pago_tarjeta": "TD"
            },
            {
                "orden": "", # Huérfano
                "factura": "T02",
                "total_pagado": 0
            }
        ]
    }
    
    # Prueba Upload Exitosa
    resp = client.post("/sync/upload/SUC_PRUEBA", json=payload)
    print("--- Upload Res:", resp.status_code, resp.json())
    
    # Prueba Deduplicación Idempotente
    resp2 = client.post("/sync/upload/SUC_PRUEBA", json=payload)
    print("--- 2nd Upload (Deduplicacion):", resp2.json())
    
    # 2. Prueba de Pausado (Tarea 2.2)
    client.post("/sync/pause/SUC_PRUEBA")
    print("--- Se aplicó Pausa a la SUC_PRUEBA.")
    
    resp_paused = client.post("/sync/upload/SUC_PRUEBA", json=payload)
    print("--- Subida bajo Pausa (Esperado 503):", resp_paused.status_code, resp_paused.json())
    
    # Reanudación
    client.post("/sync/resume/SUC_PRUEBA")
    print("--- Se aplicó Resume a SUC_PRUEBA.")
    
    # 3. Limpieza de Datos
    resp_limpieza = client.delete("/admin/limpieza/SUC_PRUEBA")
    print("--- Admin Borrado Total / Reseteo de Checkpoint:", resp_limpieza.json())
    
if __name__ == "__main__":
    test_flujos_fase2()
