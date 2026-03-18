# app/utils/prompt/prompt_mappers.py
"""
Mappers de valores enteros (columnas de parametrización de ServicioCnl)
a textos descriptivos que se inyectan en el prompt del LLM.
"""
from __future__ import annotations


# ── Mapa: in_tipo_otorgante / in_tipo_beneficiario / in_tipo_otro ─────────────
_TIPO_PERSONA_MAP: dict[int, str] = {
    0: "NO APLICA",
    1: "SOLO PERSONA NATURAL",
    2: "SOLO PERSONA JURIDICA",
    3: "PERSONA NATURAL O JURIDICA",
}

# ── Mapa: in_medio_pago / in_oportunidad_pago ─────────────────────────────────
_OBLIGATORIEDAD_MAP: dict[int, str] = {
    0: "NO APLICA",
    1: "OBLIGATORIO",
    2: "OPCIONAL",
}


def map_tipo_persona_prompt(value: int | None) -> str:
    """0→NO APLICA, 1→SOLO NATURAL, 2→SOLO JURIDICA, 3→AMBAS."""
    return _TIPO_PERSONA_MAP.get(value or 0, "NO APLICA")


def map_obligatoriedad_prompt(value: int | None) -> str:
    """0→NO APLICA, 1→OBLIGATORIO, 2→OPCIONAL."""
    return _OBLIGATORIEDAD_MAP.get(value or 0, "NO APLICA")
