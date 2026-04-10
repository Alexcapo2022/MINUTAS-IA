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
    """
    if isinstance(obj, list):
        new_list = []
        current_obj = None
        # stack para manejar anidamiento en fragmentos (ej: documento: { )
        stack = [] 

        for item in obj:
            if isinstance(item, dict):
                current_obj = repair_collapsed_json(item)
                new_list.append(current_obj)
                stack = [current_obj]
            elif isinstance(item, str):
                s = item.strip().replace('\\"', '"').rstrip(",")
                
                # Caso A: Cierre de objeto "}"
                if s == "}":
                    if len(stack) > 1: stack.pop()
                    continue
                
                # Caso B: Apertura de objeto anidado "key": {
                match_nest = re.search(r'"?([^":]+)"?\s*:\s*\{', s)
                if match_nest:
                    key = match_nest.group(1).strip().strip('"')
                    if stack:
                        new_nested = {}
                        stack[-1][key] = new_nested
                        stack.append(new_nested)
                    continue
                
                # Caso C: Campo simple "key": "value"
                match_kv = re.search(r'"?([^":]+)"?\s*:\s*(.*)', s)
                if match_kv:
                    key = match_kv.group(1).strip().strip('"')
                    val = match_kv.group(2).strip().strip('"')
                    
                    if val.lower() == "null": val = None
                    elif val.replace(".","",1).isdigit(): 
                        val = float(val) if "." in val else int(val)
                    
                    if stack:
                        stack[-1][key] = val
                    else:
                        current_obj = {key: val}
                        new_list.append(current_obj)
                        stack = [current_obj]
                else:
                    # No parece fragmento, agregamos como string normal si no es una llave suelta
                    if s not in ["{", "[", "]", "}"]:
                        new_list.append(item)
            else:
                new_list.append(repair_collapsed_json(item))
                stack = []

        return new_list

    if isinstance(obj, dict):
        return {k: repair_collapsed_json(v) for k, v in obj.items()}

    return obj
