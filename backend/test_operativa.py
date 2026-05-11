"""Tests del día operativo (corte). Ejecutar: python -m unittest backend.test_operativa -v"""
import unittest

from .operativa import (
    calcular_fecha_operacion,
    fecha_operativa_iso,
    parse_hora_to_minutes,
    widen_iso_range,
    DEFAULT_CORTE_MINUTOS,
)


class TestOperativa(unittest.TestCase):
    def test_parse_hora(self):
        self.assertEqual(parse_hora_to_minutes("06:00"), 360)
        self.assertEqual(parse_hora_to_minutes("20:30"), 20 * 60 + 30)
        self.assertEqual(parse_hora_to_minutes(""), 0)
        self.assertEqual(parse_hora_to_minutes(None), 0)

    def test_default_corte(self):
        self.assertEqual(DEFAULT_CORTE_MINUTOS, 360)

    def test_sin_corte_usa_default(self):
        # Sin corte explícito (None) ahora usa DEFAULT (360 = 06:00)
        # 03:00 < 06:00 → día anterior
        self.assertEqual(fecha_operativa_iso("2026-04-17", "03:00", None), "2026-04-16")
        # 07:00 >= 06:00 → mismo día
        self.assertEqual(fecha_operativa_iso("2026-04-17", "07:00", None), "2026-04-17")

    def test_madrugada_corte_6(self):
        # 17 abr 03:00 con corte 06:00 => día operativo 16
        self.assertEqual(fecha_operativa_iso("2026-04-17", "03:00", 360), "2026-04-16")
        self.assertEqual(fecha_operativa_iso("2026-04-17", "05:59", 360), "2026-04-16")
        self.assertEqual(fecha_operativa_iso("2026-04-17", "06:00", 360), "2026-04-17")
        self.assertEqual(fecha_operativa_iso("2026-04-17", "22:00", 360), "2026-04-17")

    def test_calcular_fecha_operacion(self):
        # Wrapper que usa el corte de la sucursal o default
        self.assertEqual(calcular_fecha_operacion("2026-05-12", "01:30", None), "2026-05-11")
        self.assertEqual(calcular_fecha_operacion("2026-05-12", "01:30", 360), "2026-05-11")
        self.assertEqual(calcular_fecha_operacion("2026-05-12", "08:00", 360), "2026-05-12")
        # Corte personalizado a las 04:00 (240 min)
        self.assertEqual(calcular_fecha_operacion("2026-05-12", "03:30", 240), "2026-05-11")
        self.assertEqual(calcular_fecha_operacion("2026-05-12", "04:00", 240), "2026-05-12")

    def test_widen(self):
        a, b = widen_iso_range("2026-04-17", "2026-04-17")
        self.assertEqual(a, "2026-04-16")
        self.assertEqual(b, "2026-04-18")


if __name__ == "__main__":
    unittest.main()
