# tests/prompt/test_service_rules_builder.py
"""
Unit tests puros para build_service_rules_text y helpers del módulo utils/prompt.
No requieren BD, no requieren FastAPI ni SQLAlchemy.
Ejecutar: python -m pytest tests/prompt/test_service_rules_builder.py -v
"""
import sys
import os

# Permite importar desde la raíz del proyecto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.utils.prompt.service_rules_builder import build_service_rules_text
from app.utils.prompt.prompt_mappers import map_tipo_persona_prompt, map_obligatoriedad_prompt


# ── Fixture: Mock de objeto ServicioCnl ──────────────────────────────────────

class MockServicio:
    """Simula un objeto ORM ServicioCnl con valores configurables."""
    def __init__(self, **kwargs):
        self.no_otorgante     = kwargs.get("no_otorgante", None)
        self.min_otorgante    = kwargs.get("min_otorgante", 0)
        self.in_tipo_otorgante = kwargs.get("in_tipo_otorgante", 0)

        self.no_beneficiario      = kwargs.get("no_beneficiario", None)
        self.min_beneficiario     = kwargs.get("min_beneficiario", 0)
        self.in_tipo_beneficiario = kwargs.get("in_tipo_beneficiario", 0)

        self.no_otro     = kwargs.get("no_otro", None)
        self.min_otro    = kwargs.get("min_otro", 0)
        self.in_tipo_otro = kwargs.get("in_tipo_otro", 0)

        self.in_medio_pago      = kwargs.get("in_medio_pago", 0)
        self.in_oportunidad_pago = kwargs.get("in_oportunidad_pago", 0)

        self.in_bienes = kwargs.get("in_bienes", 0)
        self.in_aporte_bienes = kwargs.get("in_aporte_bienes", 0)


# ── Tests: mappers ────────────────────────────────────────────────────────────

class TestPromptMappers:
    def test_tipo_persona_no_aplica(self):
        assert map_tipo_persona_prompt(0) == "NO APLICA"

    def test_tipo_persona_natural(self):
        assert map_tipo_persona_prompt(1) == "SOLO PERSONA NATURAL"

    def test_tipo_persona_juridica(self):
        assert map_tipo_persona_prompt(2) == "SOLO PERSONA JURIDICA"

    def test_tipo_persona_ambas(self):
        assert map_tipo_persona_prompt(3) == "PERSONA NATURAL O JURIDICA"

    def test_tipo_persona_none(self):
        assert map_tipo_persona_prompt(None) == "NO APLICA"

    def test_obligatoriedad_obligatorio(self):
        assert map_obligatoriedad_prompt(1) == "OBLIGATORIO"

    def test_obligatoriedad_opcional(self):
        assert map_obligatoriedad_prompt(2) == "OPCIONAL"

    def test_obligatoriedad_no_aplica(self):
        assert map_obligatoriedad_prompt(0) == "NO APLICA"


# ── Tests: build_service_rules_text ──────────────────────────────────────────

class TestBuildServiceRulesText:

    def test_none_returns_empty(self):
        """Si no hay objeto servicio, retorna cadena vacía."""
        assert build_service_rules_text(None) == ""

    def test_all_zeros_returns_empty(self):
        """Si todas las columnas están en 0, no se genera texto."""
        svc = MockServicio()
        result = build_service_rules_text(svc)
        assert result == ""

    def test_poder_solo_otorgante_natural(self):
        """PODER: 1 otorgante mínimo, solo natural."""
        svc = MockServicio(min_otorgante=1, in_tipo_otorgante=1)
        result = build_service_rules_text(svc)
        assert "OTORGANTES" in result
        assert "mínimo 1" in result
        assert "SOLO PERSONA NATURAL" in result
        assert "BENEFICIARIOS" not in result
        assert "MEDIO DE PAGO" not in result

    def test_compraventa_otorgante_beneficiario_con_pago(self):
        """COMPRA VENTA: otorgante + beneficiario + medio pago obligatorio + oportunidad."""
        svc = MockServicio(
            min_otorgante=1, in_tipo_otorgante=1,
            min_beneficiario=1, in_tipo_beneficiario=1,
            in_medio_pago=1, in_oportunidad_pago=1,
        )
        result = build_service_rules_text(svc)
        assert "OTORGANTES" in result
        assert "BENEFICIARIOS" in result
        assert "MEDIO DE PAGO" in result
        assert "OBLIGATORIO" in result
        assert "OPORTUNIDAD DE PAGO" in result

    def test_label_personalizado_otorgante(self):
        """Si no_otorgante = 'VENDEDOR', el label en el texto debe ser VENDEDOR."""
        svc = MockServicio(min_otorgante=1, in_tipo_otorgante=1, no_otorgante="VENDEDOR")
        result = build_service_rules_text(svc)
        assert "VENDEDOR" in result
        assert "OTORGANTES" not in result

    def test_label_personalizado_beneficiario(self):
        """Si no_beneficiario = 'COMPRADOR', el label debe ser COMPRADOR."""
        svc = MockServicio(
            min_otorgante=1, in_tipo_otorgante=1, no_otorgante="VENDEDOR",
            min_beneficiario=1, in_tipo_beneficiario=1, no_beneficiario="COMPRADOR",
        )
        result = build_service_rules_text(svc)
        assert "VENDEDOR" in result
        assert "COMPRADOR" in result

    def test_juridica_agrega_hint_societario(self):
        """Si el tipo incluye JURIDICA (2 o 3), debe agregar hint de RUC/razón social."""
        svc = MockServicio(min_otorgante=1, in_tipo_otorgante=2)
        result = build_service_rules_text(svc)
        assert "RUC" in result or "razón social" in result or "PERSONA JURIDICA" in result

    def test_min_otro_con_tercero(self):
        """Fiador/Garante: tercero adicional."""
        svc = MockServicio(min_otro=1, in_tipo_otro=3, no_otro="FIADOR / GARANTE")
        result = build_service_rules_text(svc)
        assert "FIADOR / GARANTE" in result
        assert "PERSONA NATURAL O JURIDICA" in result

    def test_cabecera_presente(self):
        """Cuando hay reglas, el texto debe tener la cabecera estándar."""
        svc = MockServicio(min_otorgante=1, in_tipo_otorgante=1)
        result = build_service_rules_text(svc)
        assert result.startswith("REGLAS PARAMETRIZADAS DEL SERVICIO (OBLIGATORIAS):")

    def test_medio_pago_opcional_no_agrega_hint(self):
        """Si in_medio_pago == 2 (OPCIONAL), no se agrega el hint detallado de bancos."""
        svc = MockServicio(in_medio_pago=2)
        result = build_service_rules_text(svc)
        assert "MEDIO DE PAGO" in result
        assert "OPCIONAL" in result
        assert "bancos" not in result  # el hint solo se agrega si es OBLIGATORIO (1)

    def test_min_beneficiario_zero_no_aparece(self):
        """Si min_beneficiario == 0, la sección BENEFICIARIOS no debe aparecer."""
        svc = MockServicio(min_otorgante=2, in_tipo_otorgante=1, min_beneficiario=0)
        result = build_service_rules_text(svc)
        assert "BENEFICIARIOS" not in result

    def test_bienes_simples(self):
        servicio = MockServicio(in_bienes=1)
        resultado = build_service_rules_text(servicio)
        
        assert "En la raíz 'bienes': UBICA EN EL TEXTO la tabla o lista donde se describen los bienes aportados." in resultado
        assert "REGLAS ESTRICTAS DE AGRUPACIÓN (¡LEER CON CUIDADO!):" in resultado
        assert "BIENES CON PARTIDA REGISTRAL" in resultado
        assert "BIENES SIN PARTIDA REGISTRAL" in resultado
        assert "APORTE DE CAPITAL CON BIENES (REGLA MATEMÁTICA OBLIGATORIA)" not in resultado

    def test_bienes_con_aporte_capital(self):
        servicio = MockServicio(in_bienes=2, in_aporte_bienes=1)
        resultado = build_service_rules_text(servicio)

        assert "Estado: OPCIONAL." in resultado
        assert "APORTE DE CAPITAL CON BIENES (REGLA MATEMÁTICA OBLIGATORIA)" in resultado
        assert "En 'valores.transferencia': 1 solo objeto con el monto TOTAL SUMADO" in resultado
        assert "Crea EXACTAMENTE 1 objeto por cada aportante que dio bienes" in resultado
