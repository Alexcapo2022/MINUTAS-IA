from typing import Any
from .text import clean_spaces

_UPPER_EXCLUDE_KEYS = {
    "correo",
    "email",
    "url",
    "id_evento_google",
    "id_google",
    "link_meet",
    "meet_link",
}

def uppercase_payload(obj: Any) -> Any:
    """
    Convierte a MAYÚSCULAS todos los strings del payload.
    - No toca números/bools/null.
    - Respeta keys en _UPPER_EXCLUDE_KEYS.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and k in _UPPER_EXCLUDE_KEYS:
                out[k] = v
            else:
                out[k] = uppercase_payload(v)
        return out
    if isinstance(obj, list):
        return [uppercase_payload(x) for x in obj]
    if isinstance(obj, str):
        return clean_spaces(obj).upper()
    return obj