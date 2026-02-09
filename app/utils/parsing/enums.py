import re
from difflib import SequenceMatcher
from typing import get_args

from app.schemas.enums import OportunidadPago, MedioPago, FormaPago
from .text import clean_spaces

OPORTUNIDAD_PAGO_OPTIONS = list(get_args(OportunidadPago))
MEDIO_PAGO_OPTIONS = list(get_args(MedioPago))
FORMA_PAGO_OPTIONS = list(get_args(FormaPago))

DEFAULT_OPORTUNIDAD_PAGO = "A LA FIRMA DEL INSTRUMENTO PÚBLICO NOTARIAL PROTOCOLAR"
SERVICIOS_FORMA_PAGO_CONTADO = ("COMPRA VENTA", "DONACION", "CONSTITUCION")
DEFAULT_FORMA_PAGO_PARA_ACTOS = "CONTADO"

def _norm_enum(s: str) -> str:
    s = clean_spaces((s or "").upper())
    s = re.sub(r"[^A-Z0-9ÁÉÍÓÚÑ/ \-]", "", s)
    return s

def best_match_enum(value: str, options: list[str], min_score: float = 0.72) -> str:
    v = _norm_enum(value)
    if not v:
        return ""
    best_opt = ""
    best_score = 0.0
    for opt in options:
        score = SequenceMatcher(None, v, _norm_enum(opt)).ratio()
        if score > best_score:
            best_score = score
            best_opt = opt
    return best_opt if best_score >= min_score else ""

def _servicio_match(nombre_servicio: str, needles: tuple[str, ...]) -> bool:
    s = _norm_enum(nombre_servicio)
    return bool(s) and any(n in s for n in needles)

def normalize_oportunidad_pago(value: str) -> str:
    """
    Solo normaliza si viene valor.
    - Si viene vacío => "" (NO default aquí).
    """
    value = clean_spaces(value or "")
    if not value:
        return ""
    m = best_match_enum(value, OPORTUNIDAD_PAGO_OPTIONS, min_score=0.80)
    return m or value  # si no matchea, conserva el texto original

def normalize_medio_pago_enum(value: str) -> str:
    return best_match_enum(value, MEDIO_PAGO_OPTIONS, min_score=0.72)

def normalize_forma_pago(value: str, *, nombre_servicio: str = "") -> str:
    """
    Forma de pago:
    - Si el servicio es COMPRA VENTA / DONACION / CONSTITUCION => default CONTADO.
    - Si el LLM mandó "medio de pago" acá (CHEQUE/DEPÓSITO/etc) y servicio calza => CONTADO.
    - Si viene un valor, intenta match contra FormaPago.
    - Si no calza:
        * si servicio calza => CONTADO
        * caso contrario => ""
    """
    # 1) si parece que vino "medio de pago" aquí
    maybe_medio = normalize_medio_pago_enum(value)
    if maybe_medio and _servicio_match(nombre_servicio, SERVICIOS_FORMA_PAGO_CONTADO):
        return DEFAULT_FORMA_PAGO_PARA_ACTOS

    # 2) match contra FormaPago
    m = best_match_enum(value, FORMA_PAGO_OPTIONS, min_score=0.80)
    if m:
        return m

    # 3) fallback por servicio
    if _servicio_match(nombre_servicio, SERVICIOS_FORMA_PAGO_CONTADO):
        return DEFAULT_FORMA_PAGO_PARA_ACTOS

    return ""