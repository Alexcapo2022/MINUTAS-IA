import re
from typing import Any, Optional

from ..parsing.text import clean_spaces, get_str
from ..parsing.cast import to_int_or_none
from ..common.ubicacion import normalize_ubigeo

def _norm_upper(s: str) -> str:
    return clean_spaces(s).upper()

def _map_tipo_bien(raw: str) -> str:
    r = _norm_upper(raw)
    if any(x in r for x in ["INMUEBLE", "PREDIO", "LOTE", "URBANIZ", "PARTIDA REGISTRAL", "REGISTRO DE PROPIEDAD INMUEBLE"]):
        return "INMUEBLES"
    if any(x in r for x in ["VEHIC", "PLAC", "MOTOR", "SERIE", "AUTOMOV", "CAMION", "MOTO"]):
        return "MUEBLES"
    if any(x in r for x in ["DINERO", "EFECTIVO", "SOLES", "DOLARES", "EUROS"]):
        return "DINERO EFECTIVO"
    if any(x in r for x in ["ACCION", "BONO", "VALOR", "TITULO VALOR", "PARTICIPACION", "CERTIFICADO"]):
        return "VALORES"
    return "" if not r else "OTROS"

def _map_clase_bien(raw_tipo: str, raw_clase: str, texto_ctx: str) -> str:
    ctx = _norm_upper(texto_ctx)
    t = _norm_upper(raw_tipo)
    if "INMUEBLE" in t or any(x in ctx for x in ["REGISTRO DE PROPIEDAD INMUEBLE", "PARTIDA", "URBANIZ", "LOTE"]):
        return "PREDIOS"
    if any(x in ctx for x in ["VEHIC", "PLAC", "MOTOR", "SERIE", "AUTOMOV", "CAMION", "MOTO"]):
        return "VEHICULOS TERRESTRRES"
    if any(x in ctx for x in ["NAVE", "EMBARC", "BUQUE"]):
        return "NAVES"
    if any(x in ctx for x in ["AERONAVE", "AVION", "HELICOPTERO"]):
        return "AERONAVES"
    if any(x in ctx for x in ["MINA", "CANTERA", "YACIMIENTO"]):
        return "MINAS CANTERAS Y DEPOSITOS DE HIDRO"
    if "CONCESION" in ctx:
        return "CONCESIONES"
    if any(x in ctx for x in ["PROPIEDAD INTELECTUAL", "MARCA", "PATENTE", "DERECHOS DE AUTOR"]):
        return "DERECHOS DE PROPIEAD INTELECTUAL"
    if any(x in ctx for x in ["MAQUINARIA", "EQUIPO", "MAQUINAS"]):
        return "MAQUINARIA Y EQUIPOS"
    if any(x in ctx for x in ["CREDITO", "DEUDA", "PAGARE"]):
        return "CREDITOS"
    return "OTROS NO ESPECIFICADOS" if (t or raw_clase or ctx) else "SIN OBJETOS"

def _infer_zona_registral(texto_ctx: str) -> str:
    ctx = _norm_upper(texto_ctx)
    if "LIMA-SUNARP" in ctx or "PROPIEDAD INMUEBLE DE LIMA" in ctx:
        return "LIMA"
    return ""

def _infer_distrito_inmueble(texto_ctx: str) -> str:
    m = re.search(r",\s*([A-ZÁÉÍÓÚÑ ]{3,})\s*,\s*CON UN ÁREA", _norm_upper(texto_ctx))
    if m:
        return clean_spaces(m.group(1))
    for d in ["SAN MARTIN DE PORRES", "LA MOLINA", "PUENTE PIEDRA"]:
        if d in _norm_upper(texto_ctx):
            return d
    return ""

def normalize_bien(b: dict, zona_repo: Optional[Any] = None, texto_contexto: str = "") -> dict:
    if not isinstance(b, dict):
        return b

    tipo_bien_raw = get_str(b, "tipo_bien", "tipo", default="")
    clase_bien_raw = get_str(b, "clase_bien", "clase", default="")

    partida_registral = get_str(b, "partida_registral", "partidaRegistral", default="")
    zona_registral = get_str(b, "zona_registral", "zonaRegistral", default="")
    co_zona_registral = b.get("co_zona_registral", None)

    fecha_adquisicion = get_str(b, "fecha_adquisicion", default="")
    fecha_minuta = get_str(b, "fecha_minuta", "fechaMinuta", default="")
    opcion_bien_mueble = get_str(b, "opcion_bien_mueble", "opcionBienMueble", default="")
    numero_psm = get_str(b, "numero_psm", "placaSerieMotor", default="")

    otros_bienes = ""
    ubigeo_in = b.get("ubigeo", {}) if isinstance(b.get("ubigeo"), dict) else {}
    ubigeo = normalize_ubigeo(ubigeo_in)

    # ✅ Determina si el bien "tiene señal" (para permitir inferencias)
    has_any_bien_signal = any([
        bool(tipo_bien_raw),
        bool(clase_bien_raw),
        bool(partida_registral),
        bool(zona_registral),
        bool(ubigeo.get("departamento") or ubigeo.get("provincia") or ubigeo.get("distrito")),
    ])

    # Si viene totalmente vacío, NO inventar tipo/clase/ubigeo/zona
    if not has_any_bien_signal:
        return {
            "tipo_bien": "",
            "clase_bien": "",
            "ubigeo": {"departamento": "", "provincia": "", "distrito": ""},
            "partida_registral": "",
            "zona_registral": "",
            "co_zona_registral": None,
            "fecha_adquisicion": "",
            "fecha_minuta": "",
            "opcion_bien_mueble": "",
            "numero_psm": "",
            "otros_bienes": "",
        }

    # ✅ tipo_bien SOLO si GPT lo trajo
    tipo_bien = _map_tipo_bien(tipo_bien_raw) if tipo_bien_raw else ""

    # ✅ clase_bien:
    # - Si GPT lo trajo, se respeta.
    # - Si NO lo trajo, SOLO se infiere si hay tipo_bien + ubigeo presente.
    has_ubigeo = bool(ubigeo.get("departamento") or ubigeo.get("provincia") or ubigeo.get("distrito"))
    if clase_bien_raw:
        clase_bien = clase_bien_raw
    elif tipo_bien and has_ubigeo:
        clase_bien = _map_clase_bien(tipo_bien_raw, clase_bien_raw, texto_contexto)
    else:
        clase_bien = ""

    # ✅ Zona registral: SOLO si ya hay señal (partida/zona/ubigeo) y es inmueble/ubigeo Lima
    ctx_up = _norm_upper(texto_contexto)
    is_inmueble = (tipo_bien == "INMUEBLES") or bool(partida_registral) or ("SUNARP" in ctx_up)

    if is_inmueble:
        if not zona_registral:
            zona_registral = _infer_zona_registral(texto_contexto)

        if zona_repo is not None and zona_registral and co_zona_registral is None:
            row = zona_repo.find_by_name_or_nc(zona_registral)
            if row:
                co_zona_registral = getattr(row, "co_zona_registral", None)

    return {
        "tipo_bien": tipo_bien,
        "clase_bien": clase_bien,
        "ubigeo": ubigeo,
        "partida_registral": partida_registral,
        "zona_registral": zona_registral,
        "co_zona_registral": to_int_or_none(co_zona_registral),
        "fecha_adquisicion": fecha_adquisicion,
        "fecha_minuta": fecha_minuta,
        "opcion_bien_mueble": opcion_bien_mueble,
        "numero_psm": numero_psm,
        "otros_bienes": otros_bienes,
    }