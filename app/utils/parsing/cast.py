from typing import Any, Optional

def to_int_or_none(v: Any) -> Optional[int]:
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)  # por si acaso
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        vv = v.strip()
        return int(vv) if vv.isdigit() else None
    return None