# tests/prompt/smoke_rules.py
"""
Smoke test manual para validar visualmente el texto generado por build_service_rules_text.
Ejecutar: python tests/prompt/smoke_rules.py

No requiere BD ni servidor. Imprime el bloque {{service_rules}} para cada escenario
permitiendo iterar rápidamente sobre el resultado.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.utils.prompt.service_rules_builder import build_service_rules_text


class MockServicio:
    def __init__(self, **kwargs):
        self.no_otorgante      = kwargs.get("no_otorgante", None)
        self.min_otorgante     = kwargs.get("min_otorgante", 0)
        self.in_tipo_otorgante = kwargs.get("in_tipo_otorgante", 0)

        self.no_beneficiario      = kwargs.get("no_beneficiario", None)
        self.min_beneficiario     = kwargs.get("min_beneficiario", 0)
        self.in_tipo_beneficiario = kwargs.get("in_tipo_beneficiario", 0)

        self.no_otro      = kwargs.get("no_otro", None)
        self.min_otro     = kwargs.get("min_otro", 0)
        self.in_tipo_otro = kwargs.get("in_tipo_otro", 0)

        self.in_medio_pago       = kwargs.get("in_medio_pago", 0)
        self.in_oportunidad_pago = kwargs.get("in_oportunidad_pago", 0)


SCENARIOS = [
    {
        "name": "Sin reglas (todas columnas en 0)",
        "servicio": MockServicio(),
    },
    {
        "name": "PODER — Otorgante natural + Apoderado",
        "servicio": MockServicio(
            min_otorgante=1, in_tipo_otorgante=1,
            min_beneficiario=1, in_tipo_beneficiario=1,
        ),
    },
    {
        "name": "COMPRA VENTA — Vendedor/Comprador + Pago obligatorio",
        "servicio": MockServicio(
            no_otorgante="VENDEDOR", min_otorgante=1, in_tipo_otorgante=1,
            no_beneficiario="COMPRADOR", min_beneficiario=1, in_tipo_beneficiario=1,
            in_medio_pago=1, in_oportunidad_pago=1,
        ),
    },
    {
        "name": "CONSTITUCION — Socios (juridica o natural) sin pago",
        "servicio": MockServicio(
            min_otorgante=2, in_tipo_otorgante=3,
            min_beneficiario=1, in_tipo_beneficiario=2,
        ),
    },
    {
        "name": "Con Tercero: FIADOR / GARANTE (caso de la imagen del usuario)",
        "servicio": MockServicio(
            min_otorgante=1, in_tipo_otorgante=1,
            no_otro="FIADOR / GARANTE", min_otro=1, in_tipo_otro=3,
            in_medio_pago=0, in_oportunidad_pago=0,
        ),
    },
    {
        "name": "Pago opcional sin participantes especiales",
        "servicio": MockServicio(
            in_medio_pago=2, in_oportunidad_pago=2,
        ),
    },
    {
        "name": "servicio_obj = None",
        "servicio": None,
    },
]


def _separator(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  ESCENARIO: {title}")
    print("=" * 70)


def main():
    for scenario in SCENARIOS:
        _separator(scenario["name"])
        result = build_service_rules_text(scenario["servicio"])
        if result:
            print(result)
        else:
            print("(vacío — no se inyecta nada al prompt)")


if __name__ == "__main__":
    main()
