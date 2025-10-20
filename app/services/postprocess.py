# app/services/postprocess.py
import re, hashlib
from typing import Any, Dict, List, Tuple
from app.schemas.base import ExtractMapped
from app.utils.dates import to_iso_date
from app.utils.ubigeo_online import find_ubigeo_online  # ← lookup online
import logging
log = logging.getLogger(__name__)
# =========================
#  Ruido / Normalización
# =========================
NOISE_LINES_RE = re.compile(
    r"(KARDEX:.*?$|ESCRITURA:.*?$|MINUTA\s+\d+.*?$|PAG\.\s*\d+.*?$|CRM\s*/.*?$|JTA\s*/.*?$)",
    re.IGNORECASE | re.MULTILINE
)
BULLETS_RE = re.compile(r"[•●◦]+")
EQ_RE = re.compile(r"[=]{3,}")

# ↑ ya lo tienes arriba
STOP_BENEF_MARKERS = [
    "EL PODER SE OTORGA DE ACUERDO CON LOS SIGUIENTES TÉRMINOS Y CONDICIONES",
    "EL PODER SE OTORGA DE ACUERDO CON LOS SIGUIENTES TERMINOS Y CONDICIONES",
    "TÉRMINOS Y CONDICIONES",
    "TERMINOS Y CONDICIONES",
    # NUEVOS stoppers típicos
    "PARA QUE EN NUESTRO NOMBRE",     # redactado clásico
    "PRIMERA.-", "SEGUNDA.-", "TERCERA.-",
    "FACULTADES", "FACULTADES DE SUSTITUCIÓN", "FACULTADES DE SUSTITUCION",
    "LIMA,",  # línea de lugar y fecha
    "LUGAR Y FECHA",
    "FIRMAS", "FIRMAN", "FIRMA",      # bloque de firmas
]


def clean_noise(text: str) -> str:
    if not text:
        return ""
    original = text

    t = NOISE_LINES_RE.sub("", text)
    t = BULLETS_RE.sub(" ", t)
    t = EQ_RE.sub(" ", t)
    t = re.sub(r"\s{2,}", " ", t).strip()

    # 🔒 Modo seguro: si quedó casi vacío, no limpiar
    if len(t) < max(50, int(0.05 * len(original))):
        return original.strip()
    return t

# =========================
#  A) CLASIFICACIÓN SIMPLE
# =========================
def classify_is_poder(text: str) -> float:
    keys = ["acto notarial", "poder", "escritura pública", "escritura publica"]
    hits = sum(k in (text or "").lower() for k in keys)
    return min(1.0, hits / 3)

# =========================
#  B) SANITIZADORES BASE
# =========================
def _ensure_docs_adicionales(value: Any):
    def norm_item(it: Any):
        base = {"tipo": "", "numero": "", "observaciones": ""}
        if not isinstance(it, dict):
            return base
        out = {}
        for k in base.keys():
            v = it.get(k, "")
            out[k] = v if isinstance(v, str) else ""
        return out
    if isinstance(value, list):
        return [norm_item(v) for v in value]
    if isinstance(value, dict):
        return [norm_item(value)]
    return []

def _ensure_evidence_map(value: Any):
    if not isinstance(value, dict): return {}
    out = {}
    for k, v in value.items():
        et = (v or {}).get("evidence_text", "") if isinstance(v, dict) else ""
        cs = (v or {}).get("char_span", []) if isinstance(v, dict) else []
        if not isinstance(et, str): et = ""
        if not (isinstance(cs, list) and len(cs) == 2 and all(isinstance(x,int) for x in cs)): cs = []
        out[k] = {"evidence_text": et, "char_span": cs}
    return out

def _ensure_person(obj: Any):
    base = {
        "nombres":"", "apellido_paterno":"", "apellido_materno":"",
        "nacionalidad":"", "tipo_documento":"", "numero_documento":"",
        "docs_adicionales":[], "profesion_ocupacion":"", "estado_civil":"",
        "domicilio": {"direccion":"", "ubigeo":"", "distrito":"", "provincia":"", "departamento":""},
        "role":"", "evidence":{}
    }
    if not isinstance(obj, dict):
        return base
    dom = obj.get("domicilio", {}) if isinstance(obj.get("domicilio", {}), dict) else {}
    for k in ["nombres","apellido_paterno","apellido_materno","nacionalidad","tipo_documento",
              "numero_documento","profesion_ocupacion","estado_civil","role"]:
        v = obj.get(k, "")
        base[k] = v if isinstance(v, str) else base[k]
    dom_base = base["domicilio"]
    for k in ["direccion","ubigeo","distrito","provincia","departamento"]:
        dv = dom.get(k, "")
        dom_base[k] = dv if isinstance(dv, str) else dom_base[k]
    base["domicilio"] = dom_base
    base["docs_adicionales"] = _ensure_docs_adicionales(obj.get("docs_adicionales", []))
    base["evidence"] = _ensure_evidence_map(obj.get("evidence", {}))
    return base

def _ensure_person_list(value: Any):
    if isinstance(value, list):
        return [_ensure_person(v) for v in value if isinstance(v, dict)]
    if isinstance(value, dict):
        return [_ensure_person(value)]
    return []

def sanitize_llm_out(d: Any, fallback_text_hash: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not isinstance(d, dict):
        d = {}

    out["acto"] = d.get("acto", "PODER")
    gl = d.get("generales_ley", {}) if isinstance(d.get("generales_ley", {}), dict) else {}

    out["generales_ley"] = {
        "otorgantes": _ensure_person_list(gl.get("otorgantes", gl.get("otorgante", []))),
        "beneficiarios": _ensure_person_list(gl.get("beneficiarios", gl.get("beneficiario", []))),
        "indeterminados": _ensure_person_list(gl.get("indeterminados", [])),
    }

    fecha = d.get("fecha_minuta", "")
    if not isinstance(fecha, str):
        fecha = gl.get("fecha_minuta", "") if isinstance(gl.get("fecha_minuta", ""), str) else ""
    iso, _ = to_iso_date(fecha)
    out["fecha_minuta"] = iso or (fecha if isinstance(fecha, str) else "")

    conf = d.get("confidence", {}) if isinstance(d.get("confidence", {}), dict) else {}
    campos = conf.get("campos", {}) if isinstance(conf.get("campos", {}), dict) else {}
    norm_campos = {}
    for k, v in campos.items():
        try:
            norm_campos[k] = float(v)
        except Exception:
            norm_campos[k] = 0.0
    conf["campos"] = norm_campos
    conf.setdefault("clasificacion_acto", 0.0)
    out["confidence"] = conf

    out["raw_text_hash"] = d.get("raw_text_hash", fallback_text_hash)

    # Priorizar DNI como documento principal
    for role in ["otorgantes", "beneficiarios", "indeterminados"]:
        for p in out["generales_ley"][role]:
            main_td = p.get("tipo_documento", "")
            main_nd = p.get("numero_documento", "")
            add = p.get("docs_adicionales", [])

            if (not main_td or not main_nd) and isinstance(add, list):
                dni_idx = next((i for i,x in enumerate(add) if isinstance(x, dict) and x.get("tipo","").upper().startswith("DNI")), None)
                if dni_idx is not None:
                    cand = add.pop(dni_idx)
                    p["tipo_documento"] = cand.get("tipo","")
                    p["numero_documento"] = cand.get("numero","")
                elif add:
                    cand = add.pop(0)
                    p["tipo_documento"] = p.get("tipo_documento","") or cand.get("tipo","")
                    p["numero_documento"] = p.get("numero_documento","") or cand.get("numero","")

            if isinstance(add, list) and main_td.lower().startswith("pasaporte"):
                dni_idx = next((i for i,x in enumerate(add) if isinstance(x, dict) and x.get("tipo","").upper().startswith("DNI")), None)
                if dni_idx is not None:
                    cand = add.pop(dni_idx)
                    add.append({"tipo": main_td, "numero": main_nd, "observaciones": ""})
                    p["tipo_documento"] = cand.get("tipo","")
                    p["numero_documento"] = cand.get("numero","")

            p["docs_adicionales"] = _ensure_docs_adicionales(add)

    return out

def post_validate(payload: Dict[str, Any]) -> Dict[str, Any]:
    campos = payload.setdefault("confidence", {}).setdefault("campos", {})
    for role in ["otorgantes", "beneficiarios", "indeterminados"]:
        for idx, p in enumerate(payload.get("generales_ley", {}).get(role, [])):
            ndoc = p.get("numero_documento", "")
            key = f"generales_ley.{role}[{idx}].numero_documento"
            if ndoc:
                if re.fullmatch(r"\d{8}", ndoc) or re.fullmatch(r"\d{11}", ndoc):
                    campos[key] = max(float(campos.get(key, 0.7)), 0.9)
                else:
                    campos[key] = min(float(campos.get(key, 0.6)), 0.4)
            for jdx, ad in enumerate(p.get("docs_adicionales", [])):
                num = ad.get("numero","")
                key2 = f"generales_ley.{role}[{idx}].docs_adicionales[{jdx}].numero"
                if num:
                    ok_num = (
                        (ad.get("tipo","").upper().startswith("DNI") and re.fullmatch(r"\d{8}", num)) or
                        (ad.get("tipo","").lower().startswith("ruc") and re.fullmatch(r"\d{11}", num)) or
                        (ad.get("tipo","").lower().startswith("pasaporte"))
                    )
                    campos[key2] = max(float(campos.get(key2, 0.6)), 0.85) if ok_num else min(float(campos.get(key2, 0.6)), 0.4)

    f = payload.get("fecha_minuta", "")
    if f and re.fullmatch(r"\d{4}-\d{2}-\d{2}", f):
        campos["fecha_minuta"] = max(float(campos.get("fecha_minuta", 0.7)), 0.9)
    return payload

def hash_text(raw_text: str) -> str:
    return hashlib.sha256((raw_text or "").encode("utf-8")).hexdigest()

def make_contract() -> Dict[str, Any]:
    return ExtractMapped().model_dump(exclude={"raw_text_hash"})

# ======================================================
#  C) PREPARSER DETERMINÍSTICO
# ======================================================
UPPER_NAME = r"[A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ'’\-\s]{2,}"
DNI_RE = re.compile(r"\b(D\.?N\.?I\.?|Documento\s+Nacional\s+de\s+Identidad|DNI)\s*(?:N[º°\.]|#|No\.?|Nro\.?|Nº|N°)?\s*([0-9]{8})\b", re.IGNORECASE)
DOMI_RE = re.compile(r"(?:con\s+domicilio\s+en|domiciliad[oa]\s+en|domicilio\s*:)\s+([^;:\n]+)", re.IGNORECASE)
ECIVIL_RE = re.compile(r"\b(solter[oa]|casad[oa]|divorciad[oa]|viud[oa])\b", re.IGNORECASE)
NACIO_RE = re.compile(r"de\s+nacionalidad\s+([a-záéíóúñü\-]+)", re.IGNORECASE)
PROF_RE = re.compile(r"(?:de\s+profesi[oó]n|de\s+ocupaci[oó]n)\s+([A-Za-zÁÉÍÓÚÑñü\s]+?)(?:[,;]|$)", re.IGNORECASE)
AMBOS_DOMI_RE = re.compile(r"\bamb[oa]s\b.*?\bcon\s+domicilio\s+en\s+([^;:\n]+)", re.IGNORECASE)

ADMIN_WORDS = {"DEPARTAMENTO", "PROVINCIA", "DISTRITO", "URB.", "URBANIZACIÓN", "URBANIZACION", "EL", "LA", "LOS", "LAS", "DE", "DEL", "Y"}

def _split_fullname(tokens: str) -> Tuple[str,str,str]:
    t = " ".join(tokens.split()).strip()
    parts = t.split()
    if len(parts) >= 3:
        ap_m = parts[-1]
        ap_p = parts[-2]
        nombres = " ".join(parts[:-2])
    elif len(parts) == 2:
        ap_p = parts[-1]
        ap_m = ""
        nombres = parts[0]
    else:
        nombres = parts[0] if parts else ""
        ap_p = ""
        ap_m = ""
    return nombres.title(), ap_p.title(), ap_m.title()

def looks_like_name(s: str) -> bool:
    parts = [p for p in re.split(r"\s+", s.strip()) if p]
    if len(parts) < 2:
        return False
    if parts[0].strip(".,;:").upper() in ADMIN_WORDS:
        return False
    return any(ch.isalpha() for ch in s)

def _extract_person_block(line: str) -> Dict[str, Any]:
    person = {
        "nombres": "", "apellido_paterno":"", "apellido_materno":"",
        "nacionalidad":"", "tipo_documento":"", "numero_documento":"",
        "profesion_ocupacion":"", "estado_civil":"", "domicilio":{"direccion":"","ubigeo":"","distrito":"","provincia":"","departamento":""},
        "role":"", "evidence":{"ruta.campo":{"evidence_text": line.strip(), "char_span":[]}}
    }
    # DNI obligatorio para aceptar persona útil
    mdni = DNI_RE.search(line)
    if not mdni:
        return person

    mname = re.search(UPPER_NAME, line)
    if mname and looks_like_name(mname.group(0)):
        n, ap_p, ap_m = _split_fullname(mname.group(0))
        person["nombres"] = n
        person["apellido_paterno"] = ap_p
        person["apellido_materno"] = ap_m

    person["tipo_documento"] = "DNI"
    person["numero_documento"] = mdni.group(2)

    mec = ECIVIL_RE.search(line)
    if mec:
        person["estado_civil"] = mec.group(1).upper()

    mnac = NACIO_RE.search(line)
    if mnac:
        person["nacionalidad"] = mnac.group(1).upper()

    mprof = PROF_RE.search(line)
    if mprof:
        person["profesion_ocupacion"] = mprof.group(1).strip().capitalize()

    mdom = DOMI_RE.search(line)
    if mdom:
        direccion = re.sub(r"\s*,\s*", ", ", mdom.group(1)).strip(" ,")
        person["domicilio"]["direccion"] = direccion
        low = direccion.lower()
        for key,label in [("distrito","distrito"), ("provincia","provincia"), ("departamento","departamento")]:
            m = re.search(fr"{label}\s+de\s+([a-záéíóúñü\s]+)", low, re.IGNORECASE)
            if m:
                person["domicilio"][key] = m.group(1).strip().title()

    return person

def _find_segments(text: str) -> Tuple[str,str]:
    """
    Segmenta entre 'otorga/otorgan/otorgar …' y 'a favor de …'.
    NO limpia aquí; el texto ya llega normalizado.
    """
    t = text  # ya limpio en el router

    # Bisagras más permisivas
    m_otorga = re.search(
        r"\b(?:que\s+)?otorga(?:n|r|rá|ra)?\b\s*:?\s*", 
        t, re.IGNORECASE
    )
    m_favor = re.search(
        r"\b(?:en\s+)?a\s+favor\s+de\b\s*:?\s*", 
        t, re.IGNORECASE
    )

    otorg = ""
    benef = ""

    if m_otorga and m_favor and m_favor.start() > m_otorga.end():
        otorg = t[m_otorga.end():m_favor.start()]
        benef = t[m_favor.end():]
    else:
        if m_favor:
            otorg = t[:m_favor.start()]
            benef = t[m_favor.end():]
        else:
            otorg = t

    for stop in STOP_BENEF_MARKERS:
        m_stop = re.search(re.escape(stop), benef, re.IGNORECASE)
        if m_stop:
            benef = benef[:m_stop.start()]
            break

    return otorg.strip(), benef.strip()

def preparse_roles_and_people(text: str) -> Dict[str, List[Dict[str, Any]]]:
    otorg_seg, benef_seg = _find_segments(text)
    out = {"otorgantes": [], "beneficiarios": []}

    if otorg_seg:
        amb = AMBOS_DOMI_RE.search(otorg_seg)
        ambos_dom = re.sub(r"\s*,\s*", ", ", amb.group(1)).strip(" ,") if amb else None
        chunks = re.split(r"(?:;\s*|\n+|\s+y\s+|\s*,\s*y\s+)", otorg_seg, flags=re.IGNORECASE)
        for ch in chunks:
            if DNI_RE.search(ch):
                person = _extract_person_block(ch)
                if not person.get("numero_documento"):  # por seguridad
                    continue
                if ambos_dom and not person["domicilio"]["direccion"]:
                    person["domicilio"]["direccion"] = ambos_dom
                person["role"] = "otorgante"
                out["otorgantes"].append(person)

    # Dentro de preparse_roles_and_people(...)
    if benef_seg:
        chunks = re.split(r"(?:;\s*|\n+|\s+y\s+|\s*,\s*y\s+)", benef_seg, flags=re.IGNORECASE)
        for ch in chunks:
        # ⚠️ reglas anti-ruido de firmas
            if ch.count("\t") >= 1:
                continue
            if len(DNI_RE.findall(ch)) > 1:
                continue

            if DNI_RE.search(ch):
                person = _extract_person_block(ch)
                if not person.get("numero_documento"):
                    continue
                person["role"] = "beneficiario"
                out["beneficiarios"].append(person)
    return out

def merge_with_preparsed_candidates(mapped: Dict[str, Any], candidates: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    for role in ["otorgantes", "beneficiarios"]:
        llm_list = mapped.get("generales_ley", {}).get(role, [])
        cand_list = candidates.get(role, [])

        if not llm_list and cand_list:
            mapped["generales_ley"][role] = [ _ensure_person(c) for c in cand_list ]
            continue

        n = max(len(llm_list), len(cand_list))
        merged = []
        for i in range(n):
            base = _ensure_person(llm_list[i]) if i < len(llm_list) else _ensure_person({})
            cand = _ensure_person(cand_list[i]) if i < len(cand_list) else _ensure_person({})

            def take(a,b): return a if a else b

            base["nombres"] = take(base["nombres"], cand["nombres"])
            base["apellido_paterno"] = take(base["apellido_paterno"], cand["apellido_paterno"])
            base["apellido_materno"] = take(base["apellido_materno"], cand["apellido_materno"])
            base["nacionalidad"] = take(base["nacionalidad"], cand["nacionalidad"])
            base["tipo_documento"] = take(base["tipo_documento"], cand["tipo_documento"])
            base["numero_documento"] = take(base["numero_documento"], cand["numero_documento"])
            base["profesion_ocupacion"] = take(base["profesion_ocupacion"], cand["profesion_ocupacion"])
            base["estado_civil"] = take(base["estado_civil"], cand["estado_civil"])

            for k in ["direccion","ubigeo","distrito","provincia","departamento"]:
                base["domicilio"][k] = take(base["domicilio"].get(k,""), cand["domicilio"].get(k,""))

            merged.append(base)
        mapped["generales_ley"][role] = merged

    return mapped

# ======================================================
#  D) FALLBACK DESDE EVIDENCIA
# ======================================================
NAME_COMMA_RE = re.compile(r"^\s*([A-ZÁÉÍÓÚÑ ]{2,})\s*,\s*([A-ZÁÉÍÓÚÑ ]{2,})\b")
PASSPORT_RE = re.compile(r"\bpasaporte\b.*?\b([A-Z0-9]{6,})\b", re.IGNORECASE)
RUC_RE = re.compile(r"\bRUC\s*(?:N[º°\.]|#|No\.?|Nro\.?|Nº|N°)?\s*([0-9]{11})\b", re.IGNORECASE)

def _titlecase_keep_caps(s: str) -> str:
    s = " ".join(w.strip() for w in s.split())
    return " ".join([w.capitalize() if len(w)>2 else w.lower() for w in s.split()])

def _split_name_by_comma(full: str):
    m = NAME_COMMA_RE.search(full)
    if not m:
        return "", "", ""
    apellidos = " ".join(m.group(1).strip().split())
    nombres = " ".join(m.group(2).strip().split())
    ap_tokens = apellidos.split()
    if len(ap_tokens) >= 2:
        ap_p, ap_m = ap_tokens[0], " ".join(ap_tokens[1:])
    else:
        ap_p, ap_m = apellidos, ""
    return _titlecase_keep_caps(nombres), _titlecase_keep_caps(ap_p), _titlecase_keep_caps(ap_m)

def _extract_direccion(s: str) -> str:
    m = DOMI_RE.search(s)
    if not m:
        return ""
    direccion = m.group(1)
    direccion = re.sub(r"\s*,\s*", ", ", direccion)
    direccion = re.sub(r"\s{2,}", " ", direccion).strip(" ,")
    return direccion

def _normalize_ecivil(s: str) -> str:
    m = ECIVIL_RE.search(s)
    return m.group(1).upper() if m else ""

def _extract_prof(s: str) -> str:
    m = PROF_RE.search(s)
    return m.group(1).strip().capitalize() if m else ""

def apply_fallbacks_from_evidence(payload: dict) -> dict:
    gl = payload.get("generales_ley", {})
    for role in ["otorgantes", "beneficiarios", "indeterminados"]:
        for p in gl.get(role, []):
            ev = p.get("evidence", {})
            ev_texts = []
            for v in ev.values():
                t = (v or {}).get("evidence_text", "")
                if isinstance(t, str) and len(t) > 0:
                    ev_texts.append(t)
            if not ev_texts:
                continue
            et = max(ev_texts, key=len)

            if not p.get("nombres") and (not p.get("apellido_paterno") and not p.get("apellido_materno")):
                nombres, ap_p, ap_m = _split_name_by_comma(et)
                if nombres:
                    p["nombres"] = p.get("nombres") or nombres
                    p["apellido_paterno"] = p.get("apellido_paterno") or ap_p
                    p["apellido_materno"] = p.get("apellido_materno") or ap_m

            if (not p.get("numero_documento")):
                m = DNI_RE.search(et)
                if m:
                    p["tipo_documento"] = p.get("tipo_documento") or "DNI"
                    p["numero_documento"] = m.group(2)

            if isinstance(p.get("docs_adicionales"), list):
                mp = PASSPORT_RE.search(et)
                if mp:
                    num = mp.group(1)
                    if not any((d.get("tipo","").lower().startswith("pasaporte") and d.get("numero")==num) for d in p["docs_adicionales"]):
                        p["docs_adicionales"].append({"tipo": "Pasaporte", "numero": num, "observaciones": ""})
                mr = RUC_RE.search(et)
                if mr:
                    num = mr.group(1)
                    if not any((d.get("tipo","").lower().startswith("ruc") and d.get("numero")==num) for d in p["docs_adicionales"]):
                        p["docs_adicionales"].append({"tipo": "RUC", "numero": num, "observaciones": ""})

            if not p.get("domicilio", {}).get("direccion"):
                direccion = _extract_direccion(et)
                if direccion:
                    p["domicilio"]["direccion"] = direccion

            if not p.get("estado_civil"):
                p["estado_civil"] = _normalize_ecivil(et) or p.get("estado_civil","")

            if not p.get("profesion_ocupacion"):
                p["profesion_ocupacion"] = _extract_prof(et) or p.get("profesion_ocupacion","")

    payload["generales_ley"] = gl
    return payload

# ======================================================
#  E) ENRIQUECER UBIGEO (ONLINE)
# ======================================================
def enrich_with_ubigeo(payload: Dict) -> Dict:
    gl = payload.get("generales_ley", {})
    for role in ("otorgantes", "beneficiarios", "indeterminados"):
        for p in gl.get(role, []):
            dom = p.get("domicilio", {}) or {}
            if dom.get("ubigeo"):
                continue
            dep = (dom.get("departamento") or "").strip()
            prov = (dom.get("provincia") or "").strip()
            dist = (dom.get("distrito") or "").strip()
            if dep and prov and dist:
                try:
                    code = find_ubigeo_online(dep, prov, dist)
                    log.debug(f"[ubigeo] lookup ({dep} / {prov} / {dist}) -> {code}")
                    if code:
                        dom["ubigeo"] = code
                        p["domicilio"] = dom
                except Exception as e:
                    log.warning(f"[ubigeo] fallo lookup: {e}")
    payload["generales_ley"] = gl
    return payload
