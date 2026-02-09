# app/utils/template.py
from __future__ import annotations

from typing import Any

def render_template(template: str, context: dict[str, Any]) -> str:
    """
    Reemplaza placeholders estilo {{key}} por valores string.
    No usa f-strings ni format() para evitar problemas con llaves JSON.
    """
    result = template or ""
    for k, v in (context or {}).items():
        result = result.replace(f"{{{{{k}}}}}", "" if v is None else str(v))
    return result
