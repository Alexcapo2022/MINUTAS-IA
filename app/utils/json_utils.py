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
        data = json.loads(cleaned)
        return repair_collapsed_json(data) if isinstance(data, dict) else data
    except json.JSONDecodeError as e:
        raise ValueError(f"El modelo no devolvió JSON válido. Inicio: {cleaned[:300]}") from e


def repair_collapsed_json(obj: any) -> any:
    """
    Detecta si el JSON se 'desinfló' y convirtió objetos en listas de fragmentos.
    Ej: "participantes": [ {"nombres": "A"}, "pais: PERU", "co_pais: 1" ]
    Lo reconstruye a: "participantes": [ {"nombres": "A", "pais": "PERU", "co_pais": 1} ]
    """
    if isinstance(obj, list):
        new_list = []
        last_dict = None
        
        for item in obj:
            if isinstance(item, dict):
                # Si es un dict, lo agregamos y lo marcamos como el 'actual' para recibir fragmentos
                last_dict = repair_collapsed_json(item)
                new_list.append(last_dict)
            elif isinstance(item, str) and (":" in item or "\": " in item):
                # Es un fragmento (ej: "pais: PERU" o "pais\": \"PERU\"")
                if last_dict is not None:
                    _merge_fragment_into_dict(last_dict, item)
                else:
                    # Si no hay dict previo, creamos uno nuevo
                    last_dict = {}
                    _merge_fragment_into_dict(last_dict, item)
                    new_list.append(last_dict)
            else:
                # Cualquier otra cosa (string normal, número, etc)
                new_list.append(repair_collapsed_json(item))
                last_dict = None
        return new_list

    if isinstance(obj, dict):
        return {k: repair_collapsed_json(v) for k, v in obj.items()}

    return obj

def _merge_fragment_into_dict(target: dict, fragment: str):
    """
    Parsea un fragmento tipo 'llave: valor' e intenta meterlo al dict.
    """
    # Limpiar escapes y comas sobrantes
    clean = fragment.replace('\\"', '"').strip().rstrip(",")
    
    # Caso 1: "key": "value" o "key": value
    match = re.search(r'"?([^":]+)"?\s*:\s*(.*)', clean)
    if match:
        key = match.group(1).strip().strip('"')
        val = match.group(2).strip().strip('"')
        if val.lower() == "null": val = None
        elif val.isdigit(): val = int(val)
        target[key] = val
