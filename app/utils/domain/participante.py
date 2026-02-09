# app/utils/parsing2/domain/participante.py
import re
from typing import Any, Optional, get_args

from app.schemas.enums import DepartamentosPeru

from ..parsing.text import clean_spaces, get_str
from ..parsing.cast import to_int_or_none
from ..parsing.enums import _norm_enum  # se usa para limpiar nombres vs apellidos
from ..common.documento import normalize_documento
from ..common.ubicacion import normalize_domicilio

DEPARTAMENTOS_PERU_SET = set(get_args(DepartamentosPeru))


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


# -------------------------
# Helper 1: lectura y normalización base (snake/camel, limpieza de nombres)
# -------------------------
def _extract_base_fields(p: dict) -> dict:
    tipo_persona = get_str(p, "tipo_persona", "tipoPersona", default="NATURAL")
    nombres = get_str(p, "nombres", default="")
    ap_pat = get_str(p, "apellido_paterno", "apellidoPaterno", default="")
    ap_mat = get_str(p, "apellido_materno", "apellidoMaterno", default="")
    razon_social = get_str(p, "razon_social", "razonSocial", default="")

    ciiu_in = get_str(p, "ciiu", default="")
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
    estado_civil_lookup = _normalize_estado_civil_for_catalog(estado_civil_raw)

    genero = get_str(p, "genero", default="")
    rol = get_str(p, "rol", default="")
    relacion = get_str(p, "relacion", default="")

    co_pais = get_str(p, "co_pais", default="")
    co_ocupacion = get_str(p, "co_ocupacion", default="")
    co_estado_civil = get_str(p, "co_estado_civil", "co_estadoCivil", default="")

    porcentaje_participacion = p.get("porcentaje_participacion", p.get("porcentajeParticipacion", 0.0)) or 0.0
    numero_acciones_part = p.get("numeroAcciones_participaciones", p.get("numeroAccionesParticipaciones", 0)) or 0
    acciones_suscritas = p.get("acciones_suscritas", p.get("accionesSuscritas", 0)) or 0
    monto_aportado = p.get("monto_aportado", p.get("montoAportado", 0.0)) or 0.0

    doc_in = p.get("documento", {}) if isinstance(p.get("documento"), dict) else {}
    dom_in = p.get("domicilio", {}) if isinstance(p.get("domicilio"), dict) else {}

    return {
        "tipo_persona": tipo_persona,
        "nombres": nombres,
        "apellido_paterno": ap_pat,
        "apellido_materno": ap_mat,
        "razon_social": razon_social,
        "ciiu_in": ciiu_in,
        "pais": pais,
        "ocupacion": ocupacion,
        "otros_ocupaciones": otros_ocupaciones,
        "estado_civil_raw": estado_civil_raw,
        "estado_civil_lookup": estado_civil_lookup,
        "genero": genero,
        "rol": rol,
        "relacion": relacion,
        "co_pais": co_pais,
        "co_ocupacion": co_ocupacion,
        "co_estado_civil": co_estado_civil,
        "porcentaje_participacion": porcentaje_participacion,
        "numeroAcciones_participaciones": numero_acciones_part,
        "acciones_suscritas": acciones_suscritas,
        "monto_aportado": monto_aportado,
        "doc_in": doc_in,
        "dom_in": dom_in,
    }


# -------------------------
# Helper 2: documento + domicilio + inferencia de país por ubigeo
# -------------------------
def _resolve_documento_domicilio_and_pais(base: dict, *, doc_repo: Optional[Any]) -> tuple[dict, dict, str]:
    documento = normalize_documento(base["doc_in"], doc_repo=doc_repo)
    domicilio = normalize_domicilio(base["dom_in"])

    pais = base["pais"]

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

    return documento, domicilio, pais


# -------------------------
# Helper 3: catálogos (país/ocupación/estado civil) + regla CIIU
# -------------------------
def _resolve_catalogs_and_ciiu(
    base: dict,
    *,
    ciiu_repo: Optional[Any],
    pais_repo: Optional[Any],
    ocup_repo: Optional[Any],
    ec_repo: Optional[Any],
    payload_original: dict,
) -> tuple[str, Optional[int], Any, Any, Any]:
    pais = base["pais"]
    co_pais = base["co_pais"]
    ocupacion = base["ocupacion"]
    otros_ocupaciones = base["otros_ocupaciones"]
    co_ocupacion = base["co_ocupacion"]
    estado_civil_raw = base["estado_civil_raw"]
    estado_civil_lookup = base["estado_civil_lookup"]
    co_estado_civil = base["co_estado_civil"]

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
    rol_up = (base["rol"] or "").strip().upper()
    tipo_up = (base["tipo_persona"] or "").strip().upper()
    allow_ciiu = (rol_up == "BENEFICIARIO" and tipo_up == "JURIDICA")

    if not allow_ciiu:
        ciiu = ""
        co_ciiu = None
    else:
        ciiu = clean_spaces(base["ciiu_in"])

        # co_ciiu puede venir como int o string
        co_ciiu = payload_original.get("co_ciiu", payload_original.get("coCiiu", None))
        co_ciiu = to_int_or_none(co_ciiu)

        # default seguro si viene vacío
        if not ciiu:
            ciiu = "ACTIVIDADES INMOBILIARIAS, EMPRESARIALES Y DE ALQUILER"

        if ciiu_repo is not None:
            # 1) Si viene co_ciiu pero no viene nombre, completa nombre desde BD
            if co_ciiu is not None and not ciiu:
                row = ciiu_repo.find_by_codigo(str(co_ciiu))
                if row:
                    ciiu = clean_spaces(getattr(row, "de_actividad", None) or ciiu)
                    co_ciiu = getattr(row, "co_ciiu", co_ciiu)

            # 2) Si viene nombre, calcula best match y setea ambos
            if ciiu:
                row = ciiu_repo.find_best_match(ciiu)
                if row:
                    ciiu = clean_spaces(getattr(row, "de_actividad", None) or ciiu)
                    co_ciiu = getattr(row, "co_ciiu", co_ciiu)

    # devolvemos campos actualizados
    base["pais"] = pais
    base["co_pais"] = co_pais
    base["ocupacion"] = ocupacion
    base["otros_ocupaciones"] = otros_ocupaciones
    base["co_ocupacion"] = co_ocupacion
    base["estado_civil_raw"] = estado_civil_raw
    base["co_estado_civil"] = co_estado_civil

    return ciiu, co_ciiu, co_pais, co_ocupacion, co_estado_civil


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

    # 1) base
    base = _extract_base_fields(p)

    # 2) documento/domicilio + infer pais
    documento, domicilio, pais = _resolve_documento_domicilio_and_pais(base, doc_repo=doc_repo)
    base["pais"] = pais

    # 3) catálogos + CIIU
    ciiu, co_ciiu, _, _, _ = _resolve_catalogs_and_ciiu(
        base,
        ciiu_repo=ciiu_repo,
        pais_repo=pais_repo,
        ocup_repo=ocup_repo,
        ec_repo=ec_repo,
        payload_original=p,
    )

    return {
        "tipo_persona": base["tipo_persona"],
        "nombres": base["nombres"],
        "apellido_paterno": base["apellido_paterno"],
        "apellido_materno": base["apellido_materno"],
        "razon_social": base["razon_social"],

        "ciiu": ciiu,
        "co_ciiu": (co_ciiu or None),

        "pais": base["pais"],
        "co_pais": to_int_or_none(base["co_pais"]),
        "documento": documento,
        "ocupacion": base["ocupacion"],
        "otros_ocupaciones": base["otros_ocupaciones"],
        "co_ocupacion": to_int_or_none(base["co_ocupacion"]),
        "estado_civil": base["estado_civil_raw"],
        "co_estado_civil": to_int_or_none(base["co_estado_civil"]),
        "domicilio": domicilio,
        "genero": base["genero"],
        "rol": base["rol"],
        "relacion": base["relacion"],
        "porcentaje_participacion": float(base["porcentaje_participacion"] or 0.0),
        "numeroAcciones_participaciones": int(base["numeroAcciones_participaciones"] or 0),
        "acciones_suscritas": int(base["acciones_suscritas"] or 0),
        "monto_aportado": float(base["monto_aportado"] or 0.0),
    }