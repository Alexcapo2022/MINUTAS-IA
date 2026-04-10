# tests/test_repair_logic.py
import sys
import os

# Añadimos el root al path para poder importar app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils.json_utils import repair_collapsed_json

def test_repair():
    # Simulamos el JSON malogrado que recibimos en los logs
    malformed_data = {
        "participantes": {
            "beneficiarios": [
                {
                    "tipo_persona": "JURIDICA",
                    "razon_social": "TRANSFORMACION 360 SAC"
                },
                "pais\": \"PERU\"",  # Fragmento como el del log
                "co_pais\": null, ",
                "documento\": { ",
                "tipo_documento\": \"RUC\", ",
                "numero_documento\": \"20600012345\" ",
                "}"
            ]
        }
    }

    print("--- DATA ORIGINAL MALFORMADA ---")
    print(malformed_data)

    repaired = repair_collapsed_json(malformed_data)

    print("\n--- DATA REPARADA ---")
    import json
    print(json.dumps(repaired, indent=2))

    # Verificaciones
    beneficiarios = repaired["participantes"]["beneficiarios"]
    assert len(beneficiarios) == 1, f"Debería haber solo 1 beneficiario, se encontraron {len(beneficiarios)}"
    assert beneficiarios[0]["pais"] == "PERU"
    assert beneficiarios[0].get("tipo_documento") == "RUC"
    assert beneficiarios[0].get("numero_documento") == "20600012345"

    print("\n✅ ¡PRUEBA EXITOSA! La lógica de reparación reconstruyó el objeto correctamente.")

if __name__ == "__main__":
    try:
        test_repair()
    except Exception as e:
        print(f"\n❌ FALLÓ LA PRUEBA: {e}")
        import traceback
        traceback.print_exc()
