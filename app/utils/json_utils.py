# app/utils/json_utils.py
import json
import re

def parse_json_strict(text: str) -> dict:
    """
    Intenta parsear JSON.
    Si viene con basura (```json ... ```), lo limpia.
    """
    if not text:
        raise ValueError("Respuesta vacía del modelo.")

    cleaned = text.strip()

    # Quitar fences ```json ... ```
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"El modelo no devolvió JSON válido. Inicio: {cleaned[:300]}") from e
