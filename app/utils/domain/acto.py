from ..parsing.text import get_str
from ..parsing.date_utils import normalize_date_str

def normalize_acto(acto: dict) -> dict:
    if not isinstance(acto, dict):
        return {"nombre_servicio": "", "fecha_minuta": ""}
    return {
        "nombre_servicio": get_str(acto, "nombre_servicio", default=""),
        "fecha_minuta": normalize_date_str(get_str(acto, "fecha_minuta", "fechaMinuta", default="")),
    }