# app/utils/parsing.py
import re
from typing import Any, Optional, get_args
from difflib import SequenceMatcher

from app.schemas.enums import OportunidadPago, MedioPago, FormaPago , DepartamentosPeru


def only_digits(s: str) -> str:
    return re.sub(r"\D+", "", s or "")

def clean_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def get_str(d: dict, *keys: str, default: str = "") -> str:
    """Obtiene el primer key existente como string limpio."""
    for k in keys:
        v = d.get(k, None)
        if isinstance(v, str):
            return clean_spaces(v)
        if v is not None and v != "":
            return clean_spaces(str(v))
    return default

def _clean_dict_str_fields(obj: dict, keys: tuple[str, ...]) -> None:
    for k in keys:
        if k in obj and isinstance(obj[k], str):
            obj[k] = clean_spaces(obj[k])

def _to_int_or_none(v):
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

OPORTUNIDAD_PAGO_OPTIONS = list(get_args(OportunidadPago))
MEDIO_PAGO_OPTIONS = list(get_args(MedioPago))
FORMA_PAGO_OPTIONS = list(get_args(FormaPago))
DEPARTAMENTOS_PERU_SET = set(get_args(DepartamentosPeru))
MEDIOS_PAGO_ENUM = set(get_args(MedioPago))

DEFAULT_OPORTUNIDAD_PAGO = "A LA FIRMA DEL INSTRUMENTO PÚBLICO NOTARIAL PROTOCOLAR"
SERVICIOS_FORMA_PAGO_CONTADO = ("COMPRA VENTA", "DONACION", "CONSTITUCION")
DEFAULT_FORMA_PAGO_PARA_ACTOS = "CONTADO"

def _norm_enum(s: str) -> str:
    s = clean_spaces((s or "").upper())
    s = re.sub(r"[^A-Z0-9ÁÉÍÓÚÑ/ \-]", "", s)
    return s

def best_match_enum(value: str, options: list[str], min_score: float = 0.72) -> str:
    v = _norm_enum(value)
    if not v:
        return ""
    best_opt = ""
    best_score = 0.0
    for opt in options:
        score = SequenceMatcher(None, v, _norm_enum(opt)).ratio()
        if score > best_score:
            best_score = score
            best_opt = opt
    return best_opt if best_score >= min_score else ""

def _servicio_match(nombre_servicio: str, needles: tuple[str, ...]) -> bool:
    s = _norm_enum(nombre_servicio)
    return bool(s) and any(n in s for n in needles)

def normalize_oportunidad_pago(value: str) -> str:
    """
    Solo normaliza si viene valor.
    - Si viene vacío => "" (NO default aquí).
    """
    value = clean_spaces(value or "")
    if not value:
        return ""
    m = best_match_enum(value, OPORTUNIDAD_PAGO_OPTIONS, min_score=0.80)
    return m or value  # si no matchea, conserva el texto original

def normalize_medio_pago_enum(value: str) -> str:
    return best_match_enum(value, MEDIO_PAGO_OPTIONS, min_score=0.72)

def normalize_forma_pago(value: str, *, nombre_servicio: str = "") -> str:
    """
    Forma de pago:
    - Si el servicio es COMPRA VENTA / DONACION / CONSTITUCION => default CONTADO.
    - Si el LLM mandó "medio de pago" acá (CHEQUE/DEPÓSITO/etc) y servicio calza => CONTADO.
    - Si viene un valor, intenta match contra FormaPago.
    - Si no calza:
        * si servicio calza => CONTADO
        * caso contrario => ""
    """
    # 1) si parece que vino "medio de pago" aquí
    maybe_medio = normalize_medio_pago_enum(value)
    if maybe_medio and _servicio_match(nombre_servicio, SERVICIOS_FORMA_PAGO_CONTADO):
        return DEFAULT_FORMA_PAGO_PARA_ACTOS

    # 2) match contra FormaPago
    m = best_match_enum(value, FORMA_PAGO_OPTIONS, min_score=0.80)
    if m:
        return m

    # 3) fallback por servicio
    if _servicio_match(nombre_servicio, SERVICIOS_FORMA_PAGO_CONTADO):
        return DEFAULT_FORMA_PAGO_PARA_ACTOS

    return ""

def normalize_moneda_str(raw: str) -> str:
    s = clean_spaces((raw or "")).upper()

    # --- SOLES ---
    if s in ("PEN", "S/.", "S/", "SOLES", "SOL", "NUEVOS SOLES", "NUEVO SOL"):
        return "SOLES"

    # --- DÓLARES ---
    if s in ("USD", "US$", "US$.", "$", "DOLARES", "DÓLARES", "DOLAR", "DÓLAR", "DOLARES AMERICANOS", "DOLAR AMERICANO"):
        return "DOLARES"

    # --- EUROS ---
    if s in ("EUR", "€", "EUROS", "EURO"):
        return "EUROS"

    return s

def normalize_documento(doc: dict, doc_repo: Optional[Any] = None) -> dict:
    if not isinstance(doc, dict):
        return {"co_documento": None, "tipo_documento": "", "numero_documento": ""}

    # ✅ co_documento debe ser int|None
    co_documento = _to_int_or_none(doc.get("co_documento", None))

    tipo_raw = get_str(doc, "tipo_documento", "tipo", default="")
    numero = get_str(doc, "numero_documento", "numero", default="")

    # Normaliza el tipo (incluye CE -> C.E.)
    t = clean_spaces(tipo_raw).upper()

    # Quita separadores para comparar (CE / C.E. / C E / C-E)
    t_cmp = re.sub(r"[^A-Z]", "", t)

    if t_cmp == "DNI":
        tipo = "DNI"
        numero = only_digits(numero)
    elif t_cmp == "RUC":
        tipo = "RUC"
        numero = only_digits(numero)
    elif t_cmp == "CE":
        tipo = "C.E."
        numero = only_digits(numero)
    elif t_cmp == "PAS":
        tipo = "PAS"
        # PAS a veces puede tener letras; no forzamos only_digits
    else:
        # Mantén el original limpio si no calza
        tipo = clean_spaces(tipo_raw)

    # ✅ catálogo solo si no vino co_documento
    # OJO: para buscar en repo conviene buscar por la forma normalizada
    if doc_repo is not None and co_documento is None and tipo:
        row = doc_repo.find_by_nc(tipo)
        if row:
            co_documento = _to_int_or_none(getattr(row, "co_tipo_documento", None))

    return {"co_documento": co_documento, "tipo_documento": tipo, "numero_documento": numero}

def normalize_ubigeo(ub: dict) -> dict:
    if not isinstance(ub, dict):
        return {"departamento": "", "provincia": "", "distrito": ""}

    _clean_dict_str_fields(ub, ("departamento", "provincia", "distrito"))
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

def _normalize_estado_civil_for_catalog(s: str) -> str:
    s = clean_spaces((s or "")).upper()
    mapping = {
        "SOLTERA": "SOLTERO",
        "CASADA": "CASADO",
        "DIVORCIADA": "DIVORCIADO",
        "VIUDA": "VIUDO",
        "SEPARADA": "SEPARADO",
    }
    return mapping.get(s, s)

def normalize_participante(
    p: dict,
    ciiu_repo: Optional[Any] = None,
    pais_repo: Optional[Any] = None,
    doc_repo: Optional[Any] = None,
    ocup_repo: Optional[Any] = None,
    ec_repo: Optional[Any] = None,
) -> dict:
    if not isinstance(p, dict):
        return p

    tipo_persona = get_str(p, "tipo_persona", "tipoPersona", default="NATURAL")
    nombres = get_str(p, "nombres", default="")
    ap_pat = get_str(p, "apellido_paterno", "apellidoPaterno", default="")
    ap_mat = get_str(p, "apellido_materno", "apellidoMaterno", default="")
    razon_social = get_str(p, "razon_social", "razonSocial", default="")

    # CIIU: puede venir como texto, o a veces como "F: CONSTRUCCION"
    ciiu_in = get_str(p, "ciiu", default="")
    co_ciiu_in = get_str(p, "co_ciiu", default="")  # si viniera ya el código

    pais = get_str(p, "pais", "nacionalidad", default="")

    # Si vienen apellidos por separado, limpia nombres (sin apellidos)
    if nombres and (ap_pat or ap_mat):
        n_up = _norm_enum(nombres)
        if ap_pat:
            n_up = re.sub(rf"\b{re.escape(_norm_enum(ap_pat))}\b", "", n_up)
        if ap_mat:
            n_up = re.sub(rf"\b{re.escape(_norm_enum(ap_mat))}\b", "", n_up)
        nombres = clean_spaces(n_up.title() if n_up else nombres)

    ocupacion = get_str(p, "ocupacion", "profesionOcupacion", default="")
    otros_ocupaciones = get_str(p, "otros_ocupaciones", "otrosOcupaciones", default="")

    estado_civil_raw = get_str(p, "estado_civil", "estadoCivil", default="")
    genero = get_str(p, "genero", default="")
    rol = get_str(p, "rol", default="")
    relacion = get_str(p, "relacion", default="")

    estado_civil_lookup = _normalize_estado_civil_for_catalog(estado_civil_raw)

    co_pais = get_str(p, "co_pais", default="")
    co_ocupacion = get_str(p, "co_ocupacion", default="")
    co_estado_civil = get_str(p, "co_estado_civil", "co_estadoCivil", default="")

    porcentaje_participacion = p.get("porcentaje_participacion", p.get("porcentajeParticipacion", 0.0)) or 0.0
    numeroAcciones_participaciones = p.get(
        "numeroAcciones_participaciones", p.get("numeroAccionesParticipaciones", 0)
    ) or 0
    acciones_suscritas = p.get("acciones_suscritas", p.get("accionesSuscritas", 0)) or 0
    monto_aportado = p.get("monto_aportado", p.get("montoAportado", 0.0)) or 0.0

    doc_in = p.get("documento", {}) if isinstance(p.get("documento"), dict) else {}
    documento = normalize_documento(doc_in, doc_repo=doc_repo)

    dom_in = p.get("domicilio", {}) if isinstance(p.get("domicilio"), dict) else {}
    domicilio = normalize_domicilio(dom_in)

    # ✅ Si el ubigeo parece PERÚ (cualquier departamento), y no vino país, asumimos PERU
    try:
        ub = (domicilio.get("ubigeo") or {}) if isinstance(domicilio, dict) else {}
        dep = clean_spaces((ub.get("departamento") or "")).upper()
        prov = clean_spaces((ub.get("provincia") or "")).upper()

        if (not pais) and dep in DEPARTAMENTOS_PERU_SET:
            pais = "PERU"
        elif (not pais) and (not dep) and prov in ("LIMA", "CALLAO"):
            pais = "PERU"
    except Exception:
        pass

    # -------------------------
    # Catálogos (PAÍS / OCUP / EC)
    # -------------------------
    if pais_repo is not None and pais and not co_pais:
        row = pais_repo.find_by_name(pais)
        if row:
            co_pais = getattr(row, "co_pais", None)

    if ocup_repo is not None and ocupacion and not co_ocupacion:
        original_ocup = ocupacion
        row = ocup_repo.find_by_desc(ocupacion)
        if row:
            co_ocupacion = getattr(row, "co_ocupacion", None)
            bd_desc = (getattr(row, "de_ocupacion", None) or "").strip()
            if bd_desc.upper() == "OTROS (ESPECIFICAR)":
                if not otros_ocupaciones:
                    otros_ocupaciones = original_ocup
                ocupacion = "OTROS (ESPECIFICAR)"
            else:
                ocupacion = bd_desc

    if ec_repo is not None and estado_civil_lookup and not co_estado_civil:
        row = ec_repo.find_by_name(estado_civil_lookup) or ec_repo.find_by_name(estado_civil_raw)
        if row:
            co_estado_civil = getattr(row, "co_tipo_estado_civil", None)
            estado_civil_raw = estado_civil_lookup

        # -------------------------
    # ✅ CIIU (SOLO EMPRESA CONSTITUIDA = BENEFICIARIO + JURIDICA)
    # -------------------------
    rol_up = (rol or "").strip().upper()
    tipo_up = (tipo_persona or "").strip().upper()

    allow_ciiu = (rol_up == "BENEFICIARIO" and tipo_up == "JURIDICA")

    # Si NO es empresa constituida => vaciar SIEMPRE (aunque GPT lo haya llenado)
    if not allow_ciiu:
        ciiu = ""
        co_ciiu = None
    else:
        ciiu = clean_spaces(ciiu_in)

        # co_ciiu puede venir como int o string
        co_ciiu = p.get("co_ciiu", p.get("coCiiu", None))
        co_ciiu = _to_int_or_none(co_ciiu)

        # Si viene vacío (por error del modelo), aplica default seguro (tu prompt ya lo pide, pero por si acaso)
        if not ciiu:
            ciiu = "ACTIVIDADES INMOBILIARIAS, EMPRESARIALES Y DE ALQUILER"

        # Completar desde BD
        if ciiu_repo is not None:
            # 1) Si viene co_ciiu pero no viene nombre, completa nombre desde BD
            if co_ciiu is not None and not ciiu:
                row = ciiu_repo.find_by_codigo(str(co_ciiu))
                if row:
                    ciiu = clean_spaces(getattr(row, "de_actividad", None) or ciiu)
                    co_ciiu = getattr(row, "co_ciiu", co_ciiu)

            # 2) Si viene nombre (aunque esté largo), calcula best match y setea ambos
            if ciiu:
                row = ciiu_repo.find_best_match(ciiu)
                if row:
                    ciiu = clean_spaces(getattr(row, "de_actividad", None) or ciiu)
                    co_ciiu = getattr(row, "co_ciiu", co_ciiu)
    return {
        "tipo_persona": tipo_persona,
        "nombres": nombres,
        "apellido_paterno": ap_pat,
        "apellido_materno": ap_mat,
        "razon_social": razon_social,

        # ✅ ambos campos
        "ciiu": ciiu,
        "co_ciiu": (co_ciiu or None),

        "pais": pais,
        "co_pais": _to_int_or_none(co_pais),
        "documento": documento,
        "ocupacion": ocupacion,
        "otros_ocupaciones": otros_ocupaciones,
        "co_ocupacion": _to_int_or_none(co_ocupacion),
        "estado_civil": estado_civil_raw,
        "co_estado_civil": _to_int_or_none(co_estado_civil),
        "domicilio": domicilio,
        "genero": genero,
        "rol": rol,
        "relacion": relacion,
        "porcentaje_participacion": float(porcentaje_participacion or 0.0),
        "numeroAcciones_participaciones": int(numeroAcciones_participaciones or 0),
        "acciones_suscritas": int(acciones_suscritas or 0),
        "monto_aportado": float(monto_aportado or 0.0),
    }

def normalize_transferencia(
    t: dict,
    moneda_repo: Optional[Any] = None,
    *,
    nombre_servicio: str = "",
) -> dict:
    if not isinstance(t, dict):
        return t

    moneda = normalize_moneda_str(get_str(t, "moneda", default=""))

    # ✅ co_moneda: intenta payload y luego catálogo
    co_moneda = _to_int_or_none(get_str(t, "co_moneda", default=""))

    monto = float(t.get("monto", 0.0) or 0.0)

    forma_pago_raw = get_str(t, "forma_pago", "formaPago", default="")
    forma_pago = normalize_forma_pago(forma_pago_raw, nombre_servicio=nombre_servicio)

    oportunidad_pago_raw = get_str(t, "oportunidad_pago", "oportunidadPago", default="")
    oportunidad_pago_norm = normalize_oportunidad_pago(oportunidad_pago_raw)

    # ✅ Detecta "plantilla vacía" => NO autollenar nada
    is_blank_template = (
        (moneda == "") and
        (co_moneda is None) and
        (monto == 0.0) and
        (clean_spaces(forma_pago_raw) == "") and
        (clean_spaces(oportunidad_pago_raw) == "")
    )

    if is_blank_template:
        oportunidad_pago = ""
    else:
        # ✅ Si hay evidencia de pago y oportunidad vacía => default
        has_payment_evidence = bool(moneda) or (monto > 0.0) or bool(forma_pago)
        if has_payment_evidence and not oportunidad_pago_norm:
            oportunidad_pago = DEFAULT_OPORTUNIDAD_PAGO
        else:
            oportunidad_pago = oportunidad_pago_norm

    if moneda_repo is not None and moneda and not co_moneda:
        row = moneda_repo.find_by_name(moneda)
        if row:
            co_moneda = _to_int_or_none(getattr(row, "co_tipo_moneda", None))

    return {
        "moneda": moneda,
        "co_moneda": co_moneda,
        "monto": monto,
        "forma_pago": forma_pago,
        "oportunidad_pago": oportunidad_pago,
    }

def normalize_medio_pago(m: dict, moneda_repo: Optional[Any] = None) -> dict:
    if not isinstance(m, dict):
        return m

    medio_pago_raw = get_str(m, "medio_pago", "medio", default="")
    medio_pago = normalize_medio_pago_enum(medio_pago_raw)

    moneda = normalize_moneda_str(get_str(m, "moneda", default=""))

    # ✅ co_moneda: primero intenta lo que venga del payload (string/int), y luego catálogo
    co_moneda = _to_int_or_none(get_str(m, "co_moneda", default=""))

    valor_bien = m.get("valor_bien", m.get("valorBien", 0.0)) or 0.0
    fecha_pago = get_str(m, "fecha_pago", "fechaDocumentoPago", default="")
    bancos = get_str(m, "bancos", "banco", default="")
    documento_pago = get_str(m, "documento_pago", "numeroDocumentoPago", default="")

    if moneda_repo is not None and moneda and not co_moneda:
        row = moneda_repo.find_by_name(moneda)
        if row:
            co_moneda = _to_int_or_none(getattr(row, "co_tipo_moneda", None))

    return {
        "medio_pago": medio_pago,
        "moneda": moneda,
        "co_moneda": co_moneda,  # ✅ int / None
        "valor_bien": float(valor_bien or 0.0),
        "fecha_pago": fecha_pago,
        "bancos": bancos,
        "documento_pago": documento_pago,
    }

_UPPER_EXCLUDE_KEYS = {
    "correo",
    "email",
    "url",
    "id_evento_google",
    "id_google",
    "link_meet",
    "meet_link",
}

def uppercase_payload(obj: Any) -> Any:
    """
    Convierte a MAYÚSCULAS todos los strings del payload.
    - No toca números/bools/null.
    - Respeta keys en _UPPER_EXCLUDE_KEYS.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(k, str) and k in _UPPER_EXCLUDE_KEYS:
                out[k] = v
            else:
                out[k] = uppercase_payload(v)
        return out
    if isinstance(obj, list):
        return [uppercase_payload(x) for x in obj]
    if isinstance(obj, str):
        return clean_spaces(obj).upper()
    return obj

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
        # No inventamos ubigeo LIMA por default.
        # Solo inferimos zona corta si texto lo dice (LIMA-SUNARP/PROPIEDAD INMUEBLE DE LIMA)
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
        "co_zona_registral": _to_int_or_none(co_zona_registral),
        "fecha_adquisicion": fecha_adquisicion,
        "fecha_minuta": fecha_minuta,
        "opcion_bien_mueble": opcion_bien_mueble,
        "numero_psm": numero_psm,
        "otros_bienes": otros_bienes,
    }

def normalize_acto(acto: dict) -> dict:
    if not isinstance(acto, dict):
        return {"nombre_servicio": "", "fecha_minuta": ""}
    return {
        "nombre_servicio": get_str(acto, "nombre_servicio", default=""),
        "fecha_minuta": get_str(acto, "fecha_minuta", "fechaMinuta", default=""),
    }

def normalize_payload(
    payload: dict,
    ciiu_repo: Optional[Any] = None,
    pais_repo: Optional[Any] = None,
    doc_repo: Optional[Any] = None,
    ocup_repo: Optional[Any] = None,
    ec_repo: Optional[Any] = None,
    moneda_repo: Optional[Any] = None,
    zona_repo: Optional[Any] = None,
    texto_contexto: str = "",
    nombre_servicio: str = "",
) -> dict:
    if not isinstance(payload, dict):
        return payload

    obj = payload
    while isinstance(obj, dict) and "payload" in obj and isinstance(obj["payload"], dict):
        obj = obj["payload"]

    if not isinstance(obj, dict):
        return payload

    obj["acto"] = normalize_acto(obj.get("acto", {}) if isinstance(obj.get("acto"), dict) else {})

    participantes = obj.get("participantes", {})
    if not isinstance(participantes, dict):
        participantes = {"otorgantes": [], "beneficiarios": []}

    otorgantes = participantes.get("otorgantes", [])
    beneficiarios = participantes.get("beneficiarios", [])

    participantes["otorgantes"] = [
        normalize_participante(
            p,
            ciiu_repo=ciiu_repo,
            pais_repo=pais_repo,
            doc_repo=doc_repo,
            ocup_repo=ocup_repo,
            ec_repo=ec_repo,
        )
        for p in (otorgantes if isinstance(otorgantes, list) else [])
    ]
    participantes["beneficiarios"] = [
        normalize_participante(
            p,
            ciiu_repo=ciiu_repo,
            pais_repo=pais_repo,
            doc_repo=doc_repo,
            ocup_repo=ocup_repo,
            ec_repo=ec_repo,
        )
        for p in (beneficiarios if isinstance(beneficiarios, list) else [])
    ]
    obj["participantes"] = participantes

    valores = obj.get("valores", {})
    if not isinstance(valores, dict):
        valores = {"transferencia": [], "medioPago": []}

    transferencia = valores.get("transferencia", [])
    medio_pago = valores.get("medioPago", [])

    valores["transferencia"] = [
        normalize_transferencia(t, moneda_repo=moneda_repo, nombre_servicio=nombre_servicio)
        for t in (transferencia if isinstance(transferencia, list) else [])
    ]
    valores["medioPago"] = [
        normalize_medio_pago(m, moneda_repo=moneda_repo) for m in (medio_pago if isinstance(medio_pago, list) else [])
    ]
    obj["valores"] = valores

    bienes_in = obj.get("bienes", [])
    obj["bienes"] = [
        normalize_bien(b, zona_repo=zona_repo, texto_contexto=texto_contexto)
        for b in (bienes_in if isinstance(bienes_in, list) else [])
    ]

    # ✅ al final, convierte todo a MAYÚSCULAS
    return uppercase_payload(obj)