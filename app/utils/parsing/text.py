import re

def only_digits(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def clean_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def get_str(d: dict, *keys: str, default: str = "") -> str:
    """Obtiene el primer key existente como string limpio."""
    for k in keys:
        v = d.get(k, None)
        if isinstance(v, str):
            return clean_spaces(v)
        if v is not None and v != "":
            return clean_spaces(str(v))
    return default

def clean_dict_str_fields(obj: dict, keys: tuple[str, ...]) -> None:
    for k in keys:
        if k in obj and isinstance(obj[k], str):
            obj[k] = clean_spaces(obj[k])