from typing import Any, Optional

from ..parsing.text import clean_spaces, get_str
from ..parsing.cast import to_int_or_none
from ..parsing.enums import (
    DEFAULT_OPORTUNIDAD_PAGO,
    normalize_forma_pago,
    normalize_oportunidad_pago,
    normalize_medio_pago_enum,
)

DEFAULT_MEDIO_PAGO = "DEPOSITO EN CUENTA"


def _to_float(v: Any) -> float:
    try:
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            s = v.strip().replace(",", "")
            return float(s) if s else 0.0
        return 0.0
    except Exception:
        return 0.0

def _resolve_medio_pago(medio_pago_raw: str, valor_bien: float) -> str:
    """
    Regla:
    - Si valor_bien <= 0 => medio_pago = "" (sin autocompletar)
    - Si valor_bien > 0:
        - si viene vacío => DEFAULT_MEDIO_PAGO
        - si viene texto => fuzzy match; si no matchea => DEFAULT_MEDIO_PAGO
    """
    has_valor = valor_bien > 0.0
    raw = clean_spaces(medio_pago_raw or "")

    if not has_valor:
        return ""

    if not raw:
        return DEFAULT_MEDIO_PAGO

    matched = normalize_medio_pago_enum(raw)  # usa tu lógica actual (enums.py)
    return matched or DEFAULT_MEDIO_PAGO

def normalize_moneda_str(raw: str) -> str:
    s = clean_spaces((raw or "")).upper()

    # --- SOLES ---
    if s in ("PEN", "S/.", "S/", "SOLES", "SOL", "NUEVOS SOLES", "NUEVO SOL"):
        return "SOLES"

    # --- DÓLARES ---
    if s in ("USD", "US$", "US$.", "$", "DOLARES", "DÓLARES", "DOLAR", "DÓLAR", "DOLARES AMERICANOS", "DOLAR AMERICANO"):
        return "DOLARES"

    # --- EUROS ---
    if s in ("EUR", "€", "EUROS", "EURO"):
        return "EUROS"

    return s

def normalize_transferencia(
    t: dict,
    moneda_repo: Optional[Any] = None,
    *,
    nombre_servicio: str = "",
) -> dict:
    if not isinstance(t, dict):
        return t

    moneda = normalize_moneda_str(get_str(t, "moneda", default=""))

    # ✅ co_moneda: intenta payload y luego catálogo
    co_moneda = to_int_or_none(get_str(t, "co_moneda", default=""))

    monto = float(t.get("monto", 0.0) or 0.0)

    forma_pago_raw = get_str(t, "forma_pago", "formaPago", default="")
    forma_pago = normalize_forma_pago(forma_pago_raw, nombre_servicio=nombre_servicio)

    oportunidad_pago_raw = get_str(t, "oportunidad_pago", "oportunidadPago", default="")
    oportunidad_pago_norm = normalize_oportunidad_pago(oportunidad_pago_raw)

    # ✅ Detecta "plantilla vacía" => NO autollenar nada
    is_blank_template = (
        (moneda == "") and
        (co_moneda is None) and
        (monto == 0.0) and
        (clean_spaces(forma_pago_raw) == "") and
        (clean_spaces(oportunidad_pago_raw) == "")
    )

    if is_blank_template:
        oportunidad_pago = ""
    else:
        # ✅ Si hay evidencia de pago y oportunidad vacía => default
        has_payment_evidence = bool(moneda) or (monto > 0.0) or bool(forma_pago)
        if has_payment_evidence and not oportunidad_pago_norm:
            oportunidad_pago = DEFAULT_OPORTUNIDAD_PAGO
        else:
            oportunidad_pago = oportunidad_pago_norm

    if moneda_repo is not None and moneda and not co_moneda:
        row = moneda_repo.find_by_name(moneda)
        if row:
            co_moneda = to_int_or_none(getattr(row, "co_tipo_moneda", None))

    return {
        "moneda": moneda,
        "co_moneda": co_moneda,
        "monto": monto,
        "forma_pago": forma_pago,
        "oportunidad_pago": oportunidad_pago,
    }

def normalize_medio_pago(m: dict, moneda_repo: Optional[Any] = None) -> dict:
    if not isinstance(m, dict):
        return m

    medio_pago_raw = get_str(m, "medio_pago", "medio", default="")

    moneda = normalize_moneda_str(get_str(m, "moneda", default=""))

    # ✅ co_moneda: primero intenta lo que venga del payload (string/int), y luego catálogo
    co_moneda = to_int_or_none(get_str(m, "co_moneda", default=""))

    valor_bien_raw = m.get("valor_bien", m.get("valorBien", 0.0))
    valor_bien = _to_float(valor_bien_raw)

    # ✅ regla nueva sin tocar enums.py
    medio_pago = _resolve_medio_pago(medio_pago_raw, valor_bien)

    fecha_pago = get_str(m, "fecha_pago", "fechaDocumentoPago", default="")
    bancos = get_str(m, "bancos", "banco", default="")
    documento_pago = get_str(m, "documento_pago", "numeroDocumentoPago", default="")

    if moneda_repo is not None and moneda and not co_moneda:
        row = moneda_repo.find_by_name(moneda)
        if row:
            co_moneda = to_int_or_none(getattr(row, "co_tipo_moneda", None))

    return {
        "medio_pago": medio_pago,
        "moneda": moneda,
        "co_moneda": co_moneda,  # ✅ int / None
        "valor_bien": float(valor_bien or 0.0),
        "fecha_pago": fecha_pago,
        "bancos": bancos,
        "documento_pago": documento_pago,
    }