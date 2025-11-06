import re

def only_digits(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def clean_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def normalize_person(person: dict) -> dict:
    # Normalizaciones mínimas seguras (no inventar datos)
    if "numeroDocumento" in person:
        person["numeroDocumento"] = only_digits(person["numeroDocumento"])
    # Limpieza de espacios
    for key in ("nombres","apellidoPaterno","apellidoMaterno","nacionalidad",
                "tipoDocumento","profesionOcupacion","estadoCivil"):
        if key in person and isinstance(person[key], str):
            person[key] = clean_spaces(person[key])
    if "domicilio" in person and isinstance(person["domicilio"], dict):
        dom = person["domicilio"]
        if "direccion" in dom and isinstance(dom["direccion"], str):
            dom["direccion"] = clean_spaces(dom["direccion"])
        if "ubigeo" in dom and isinstance(dom["ubigeo"], dict):
            for k in ("distrito","provincia","departamento"):
                if k in dom["ubigeo"] and isinstance(dom["ubigeo"][k], str):
                    dom["ubigeo"][k] = clean_spaces(dom["ubigeo"][k])
    return person

def normalize_payload(payload: dict) -> dict:
    for array_key in ("otorgantes","beneficiarios"):
        if array_key in payload and isinstance(payload[array_key], list):
            payload[array_key] = [normalize_person(p) for p in payload[array_key]]
    return payload
