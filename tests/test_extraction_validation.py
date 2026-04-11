# tests/test_extraction_validation.py
import sys
import os
import unittest
from unittest.mock import MagicMock

# Añadimos el root al path para poder importar app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils.json_utils import repair_collapsed_json
from app.utils.parsing.payload import normalize_payload

class TestExtractionValidation(unittest.TestCase):

    def test_json_repair_complex(self):
        """Prueba que el reparador maneje anidamiento profundo y fragmentos sucios."""
        malformed = {
            "participantes": {
                "otorgantes": [
                    {
                        "nombres": "JUAN PEREZ"
                    },
                    "documento\": { ", # Fragmento que abre el contexto
                    "tipo_documento\": \"DNI\", ",
                    "numero_documento\": \"12345678\"",
                    "}", # Cierre de documento
                    "domicilio\": { ",
                    "direccion\": \"AV. SIEMPRE VIVA 123\"",
                    "}" # Cierre de domicilio
                ]
            }
        }
        repaired = repair_collapsed_json(malformed)
        otorgante = repaired["participantes"]["otorgantes"][0]
        
        self.assertEqual(otorgante["documento"]["numero_documento"], 12345678)
        self.assertEqual(otorgante["domicilio"]["direccion"], "AV. SIEMPRE VIVA 123")
        self.assertEqual(len(repaired["participantes"]["otorgantes"]), 1)

    def test_normalization_uppercase(self):
        """Verifica que el normalizador convierta todo a MAYÚSCULAS y limpie espacios."""
        raw = {
            "acto": { "nombre_servicio": "  constitucion de empresa  " },
            "participantes": {
                "otorgantes": [
                    { "nombres": "juan manuel", "apellido_paterno": "perez" }
                ]
            }
        }
        normalized = normalize_payload(raw)
        
        self.assertEqual(normalized["acto"]["nombre_servicio"], "CONSTITUCION DE EMPRESA")
        self.assertEqual(normalized["participantes"]["otorgantes"][0]["nombres"], "JUAN MANUEL")

    def test_reconciliacion_financiera(self):
        """Prueba que los montos se sincronicen entre transferencia y medioPago."""
        raw = {
            "valores": {
                "transferencia": [ { "monto": 1500.0, "moneda": "SOLES" } ],
                "medioPago": [ { "medio_pago": "DEPOSITO EN CUENTA", "valor_bien": 0.0 } ]
            }
        }
        normalized = normalize_payload(raw)
        
        # El normalizador debería haber movido el 1500.0 al medio de pago
        self.assertEqual(normalized["valores"]["medioPago"][0]["valor_bien"], 1500.0)

    def test_limit_objeto_empresa(self):
        """Verifica que el objeto social se trunque a 2000 caracteres."""
        long_text = "OBJETO " * 500 # > 3000 chars
        raw = {
            "participantes": {
                "beneficiarios": [
                    { "tipo_persona": "JURIDICA", "objeto_empresa": long_text }
                ]
            }
        }
        normalized = normalize_payload(raw)
        objeto = normalized["participantes"]["beneficiarios"][0]["objeto_empresa"]
        
        self.assertLessEqual(len(objeto), 2000)

if __name__ == "__main__":
    unittest.main()
