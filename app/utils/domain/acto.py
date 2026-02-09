from ..parsing.text import get_str

def normalize_acto(acto: dict) -> dict:
    if not isinstance(acto, dict):
        return {"nombre_servicio": "", "fecha_minuta": ""}
    return {
        "nombre_servicio": get_str(acto, "nombre_servicio", default=""),
        "fecha_minuta": get_str(acto, "fecha_minuta", "fechaMinuta", default=""),
    }