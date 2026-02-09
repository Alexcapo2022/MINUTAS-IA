import re
from typing import Any, Optional

from app.utils.parsing.cast import to_int_or_none
from app.utils.parsing.text import clean_spaces, get_str, only_digits


def normalize_documento(doc: dict, doc_repo: Optional[Any] = None) -> dict:
    if not isinstance(doc, dict):
        return {"co_documento": None, "tipo_documento": "", "numero_documento": ""}

    # ✅ co_documento debe ser int|None
    co_documento = to_int_or_none(doc.get("co_documento", None))

    tipo_raw = get_str(doc, "tipo_documento", "tipo", default="")
    numero = get_str(doc, "numero_documento", "numero", default="")

    # Normaliza el tipo (incluye CE -> C.E.)
    t = clean_spaces(tipo_raw).upper()

    # Quita separadores para comparar (CE / C.E. / C E / C-E)
    t_cmp = re.sub(r"[^A-Z]", "", t)

    if t_cmp == "DNI":
        tipo = "DNI"
        numero = only_digits(numero)
    elif t_cmp == "RUC":
        tipo = "RUC"
        numero = only_digits(numero)
    elif t_cmp == "CE":
        tipo = "C.E."
        numero = only_digits(numero)
    elif t_cmp == "PAS":
        tipo = "PAS"
        # PAS a veces puede tener letras; no forzamos only_digits
    else:
        # Mantén el original limpio si no calza
        tipo = clean_spaces(tipo_raw)

    # ✅ catálogo solo si no vino co_documento
    # OJO: para buscar en repo conviene buscar por la forma normalizada
    if doc_repo is not None and co_documento is None and tipo:
        row = doc_repo.find_by_nc(tipo)
        if row:
            co_documento = to_int_or_none(getattr(row, "co_tipo_documento", None))

    return {"co_documento": co_documento, "tipo_documento": tipo, "numero_documento": numero}