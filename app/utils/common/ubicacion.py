from ..parsing.text import get_str, clean_dict_str_fields

def normalize_ubigeo(ub: dict) -> dict:
    if not isinstance(ub, dict):
        return {"departamento": "", "provincia": "", "distrito": ""}

    clean_dict_str_fields(ub, ("departamento", "provincia", "distrito"))
    return {
        "departamento": get_str(ub, "departamento", default=""),
        "provincia": get_str(ub, "provincia", default=""),
        "distrito": get_str(ub, "distrito", default=""),
    }

def normalize_domicilio(dom: dict) -> dict:
    if not isinstance(dom, dict):
        return {"direccion": "", "ubigeo": {"departamento": "", "provincia": "", "distrito": ""}}

    direccion = get_str(dom, "direccion", default="")
    ubigeo = normalize_ubigeo(dom.get("ubigeo", {}) if isinstance(dom.get("ubigeo"), dict) else {})
    return {"direccion": direccion, "ubigeo": ubigeo}