from typing import List, Literal, Optional
from fastapi import UploadFile
from pydantic import BaseModel

from app.utils.ingestion import get_text_from_upload
from app.utils.gpt_client import extract_donacion_text
from app.utils.parsing import normalize_payload

# ============
# Tipos base
# ============

Moneda = Literal["SOLES", "DOLARES AMERICANOS", "EUROS"]
TipoDocPN = Literal["DNI", "CE", "PAS"]
TipoDocPJ = Literal["RUC", "OTRO"]
MedioPagoEnum = Literal["Transferencia", "Cheque", "Depósito", "Efectivo", "Otro"]
TipoBienEnum = Literal["Mueble", "Inmueble", "Dinero", "Otro", "BIENES"]

FormaPagoEnum = Literal["Donación", "Anticipo"]

from typing import List, Literal, Optional
from fastapi import UploadFile
from pydantic import BaseModel

# ... (resto de imports y helpers igual)

Genero = Literal["MASCULINO", "FEMENINO"]
RolDonacion = Literal["DONANTE", "DONATARIO"]


# Definir las clases y tipos que se utilizan en el procesamiento
class Ubigeo(BaseModel):
    departamento: str = ""
    provincia: str = ""
    distrito: str = ""

class Domicilio(BaseModel):
    direccion: str = ""
    ubigeo: Ubigeo = Ubigeo()

class DocumentoPN(BaseModel):
    tipo: str  # "DNI", "CE", "PAS"
    numero: str

class EmpresaRepresentada(BaseModel):
    razonSocial: str = ""
    ruc: str = ""
    partidaElectronica: str = ""
    oficinaRegistral: str = ""
    domicilio: Domicilio = Domicilio()
    ciiu: List[str] = []

class PersonaDonacion(BaseModel):
    nombres: str = ""
    apellidoPaterno: str = ""
    apellidoMaterno: str = ""
    nacionalidad: str = ""
    documento: DocumentoPN
    profesionOcupacion: str = ""
    estadoCivil: str = ""
    domicilio: Domicilio = Domicilio()
    genero: str  # "MASCULINO" o "FEMENINO"
    porcentajeParticipacion: float = 0.0
    numeroAccionesParticipaciones: int = 0
    rol: str  # "DONANTE" o "DONATARIO"
    empresaRepresentada: EmpresaRepresentada | None = None
    relacion: str = "TITULAR"  # "TITULAR" o "REPRESENTANTE"

class Transferencia(BaseModel):
    moneda: str  # "SOLES", "DOLARES AMERICANOS", "EUROS"
    monto: float = 0.0
    formaPago: str = "Donación"  # "Donación" o "Anticipo"
    oportunidadPago: str = ""

class MedioPagoItem(BaseModel):
    medio: str  # "Transferencia", "Cheque", "Depósito", "Efectivo", "Otro"
    moneda: str  # "SOLES", "DOLARES AMERICANOS", "EUROS"
    valorBien: float = 0.0

class Bien(BaseModel):
    tipo: str  # "Mueble", "Inmueble", "Dinero", "Otro", "BIENES"
    clase: str = ""
    ubigeo: Ubigeo = Ubigeo()
    partidaElectronica: str = ""
    zonaRegistral: str = ""
    opcionBienMueble: str = ""
    placaSerieMotor: str = ""
    otrosNoEspecificado: str = ""

class DonacionResponse(BaseModel):
    tipoDocumento: str  # "Donación"
    fechaMinuta: str | None = None
    otorgantes: List[PersonaDonacion] = []
    beneficiarios: List[PersonaDonacion] = []
    transferencia: List[Transferencia] = []
    medioPago: List[MedioPagoItem] = []
    bien: List[Bien] = []



# ============ 
# Helpers 
# ============

def _norm_moneda(x: str) -> str:
    s = (x or "").strip().upper()
    if any(k in s for k in ["PEN", "SOL", "SOLES", "S/", "S/."]):
        return "SOLES"
    if any(k in s for k in ["USD", "US$", "USD$", "$", "DOLAR", "DÓLAR", "DOLARES", "DÓLARES"]):
        return "DOLARES AMERICANOS"
    if any(k in s for k in ["EUR", "€", "EURO", "EUROS"]):
        return "EUROS"
    return "SOLES"


def _map_forma_to_medio(forma: str) -> str:
    f = (forma or "").strip().lower()
    if "efectivo" in f:
        return "Efectivo"
    if "depós" in f or "deposit" in f:
        return "Depósito"
    if "transf" in f:
        return "Transferencia"
    if "cheq" in f:
        return "Cheque"
    return "Otro"


def _norm_tipo_bien(x: str) -> str:
    s = (x or "").strip().upper()
    if "INMUEB" in s:
        return "Inmueble"
    if "MUEBLE" in s:
        return "Mueble"
    if "DINERO" in s:
        return "Dinero"
    if "OTRO" in s:
        return "Otro"
    if "BIEN" in s:
        return "BIENES"
    return "BIENES"


def _fix_nacionalidad(persona: dict) -> dict:
    """
    Si nacionalidad viene vacía, tiene DNI y ubigeo con departamento,
    asumimos 'PERUANA'.
    """
    nac = (persona.get("nacionalidad") or "").strip()
    if nac:
        return persona

    doc = (persona.get("documento") or {}) or {}
    tipo_doc = (doc.get("tipo") or "").upper()
    dom = (persona.get("domicilio") or {}) or {}
    ubi = (dom.get("ubigeo") or {}) or {}
    departamento = (ubi.get("departamento") or "").strip()

    if tipo_doc == "DNI" and departamento:
        persona["nacionalidad"] = "PERUANA"

    return persona


def _fix_doc_and_genero(persona: dict) -> dict:
    """
    - Si documento.tipo viene vacío o inválido → lo normalizamos a DNI / CE / PAS.
    - Si genero viene vacío o inválido → lo normalizamos a MASCULINO / FEMENINO.
    """
    # --- Documento ---
    doc = (persona.get("documento") or {}) or {}
    tipo = (doc.get("tipo") or "").strip().upper()
    numero = (doc.get("numero") or "").strip()

    if tipo not in {"DNI", "CE", "PAS"}:
        # Heurística simple:
        # - Si el número tiene longitud distinta a 8, asumimos CE
        # - Si contiene letras, también asumimos CE
        # - En otro caso, DNI
        if any(ch.isalpha() for ch in numero) or len(numero) != 8:
            tipo = "CE"
        else:
            tipo = "DNI"
        doc["tipo"] = tipo
        persona["documento"] = doc

    # --- Género ---
    genero = (persona.get("genero") or "").strip().upper()
    if genero not in {"MASCULINO", "FEMENINO"}:
        nombre = (persona.get("nombres") or "").strip().upper()
        # Heurística básica: si termina en "A" → FEMENINO, si no → MASCULINO
        if nombre.endswith("A"):
            genero = "FEMENINO"
        else:
            genero = "MASCULINO"
        persona["genero"] = genero

    return persona


def _fix_persona_full(persona: dict) -> dict:
    """
    Aplica todas las normalizaciones de persona:
    - documento.tipo
    - genero
    - nacionalidad
    """
    p = dict(persona or {})
    p = _fix_doc_and_genero(p)
    p = _fix_nacionalidad(p)
    return p


# ====================
# Controller
# ====================

async def parse_donacion(file: UploadFile) -> DonacionResponse:
    """
    Recibe PDF o Word (DOC/DOCX) de una minuta de DONACIÓN
    y retorna el JSON estructurado para alimentar tu tabla.
    """
    texto = await get_text_from_upload(file)
    raw = await extract_donacion_text(contenido=texto, fecha_minuta_hint=None)
    cleaned = normalize_payload(raw)

    # ==========================
    # 1) medioPago + transferencia
    # ==========================
    raw_medio = cleaned.get("medioPago") or []
    raw_trans = cleaned.get("transferencia") or []

    if not raw_medio and raw_trans:
        raw_medio = [{
            "medio": _map_forma_to_medio(t.get("formaPago", "")),
            "moneda": _norm_moneda(t.get("moneda") or "SOLES"),
            "valorBien": float(t.get("monto") or 0.0),
        } for t in raw_trans]

    medio_pago = [{
        "medio": (m.get("medio") or "Otro"),
        "moneda": _norm_moneda(m.get("moneda") or "SOLES"),
        "valorBien": float(m.get("valorBien") or 0.0),
    } for m in raw_medio]

    total = round(sum(m["valorBien"] for m in medio_pago), 2)
    moneda_base = medio_pago[0]["moneda"] if medio_pago else "SOLES"

    cleaned["medioPago"] = medio_pago
    cleaned["transferencia"] = [{
        "moneda": moneda_base,
        "monto": total,
        "formaPago": (raw_trans[0].get("formaPago") if raw_trans else "Donación") or "Donación",
        "oportunidadPago": (raw_trans[0].get("oportunidadPago") if raw_trans else "") or "",
    }]

    # ==========================
    # 2) BIEN: mantener TODOS los bienes
    # ==========================
    raw_bienes = cleaned.get("bien") or []
    bienes_norm = []

    if raw_bienes:
        for b in raw_bienes:
            b0 = dict(b or {})
            ubi = (b0.get("ubigeo") or {}) or {}
            bien_item = {
                "tipo": _norm_tipo_bien(b0.get("tipo") or "BIENES"),
                "clase": b0.get("clase") or "",
                "ubigeo": ubi,
                "partidaElectronica": b0.get("partidaElectronica") or "",
                "zonaRegistral": b0.get("zonaRegistral") or "",
                "opcionBienMueble": b0.get("opcionBienMueble") or "",
                "placaSerieMotor": b0.get("placaSerieMotor") or "",
                "otrosNoEspecificado": b0.get("otrosNoEspecificado") or "",
            }
            # zonaRegistral = departamento si está vacía
            dep = (ubi.get("departamento") or "").strip()
            if dep and not bien_item["zonaRegistral"].strip():
                bien_item["zonaRegistral"] = dep
            bienes_norm.append(bien_item)
    else:
        bienes_norm = [{
            "tipo": "BIENES",
            "clase": "",
            "ubigeo": {},
            "partidaElectronica": "",
            "zonaRegistral": "",
            "opcionBienMueble": "",
            "placaSerieMotor": "",
            "otrosNoEspecificado": "",
        }]

    cleaned["bien"] = bienes_norm

    # ==========================
    # 3) Otorgantes / Beneficiarios con rol + empresaRepresentada
    # ==========================
    try:
        ot_pn = cleaned.get("otorgantePN") or []
        ot_pj = cleaned.get("otorgantePJ") or []
        ben_pn = cleaned.get("beneficiarioPN") or []
        ben_pj = cleaned.get("beneficiarioPJ") or []

        def _persona_key(p: dict) -> tuple:
            doc = ((p.get("documento") or {}).get("numero") or "").strip()
            return (
                doc,
                (p.get("nombres") or "").strip().upper(),
                (p.get("apellidoPaterno") or "").strip().upper(),
                (p.get("apellidoMaterno") or "").strip().upper(),
            )

        # --- 3.1 Otorgantes (PN) ---
        otorgantes_map: dict[tuple, dict] = {}
        for p in ot_pn:
            p2 = _fix_persona_full(p)
            p2["rol"] = "DONANTE"
            p2.setdefault("empresaRepresentada", None)
            p2["relacion"] = "TITULAR"  # Asumimos que son titulares si no tienen representante
            otorgantes_map[_persona_key(p2)] = p2

        # --- helper para crear objeto empresaRepresentada desde una PJ ---
        def _build_empresa_from_pj(pj: dict) -> dict:
            doc_pj = pj.get("documento") or {}
            return {
                "razonSocial": pj.get("razonSocial") or "",
                "ruc": (doc_pj.get("numero") or "").strip(),
                "partidaElectronica": pj.get("partidaElectronica") or "",
                "oficinaRegistral": pj.get("oficinaRegistral") or "",
                "domicilio": pj.get("domicilio") or {
                    "direccion": "",
                    "ubigeo": {"departamento": "", "provincia": "", "distrito": ""}
                },
                "ciiu": pj.get("ciiu") or [],
            }

        # --- 3.2 Representantes de otorgantePJ → DONANTE con empresaRepresentada ---
        for pj in ot_pj:
            pj_dict = dict(pj or {})
            rep = pj_dict.get("representante") or None
            if not rep:
                continue
            rep2 = _fix_persona_full(rep)
            rep2["rol"] = "DONANTE"
            rep2["relacion"] = "REPRESENTANTE"  # Aquí indicamos que es un representante
            rep2.setdefault("empresaRepresentada", None)

            empresa = _build_empresa_from_pj(pj_dict)
            rep2["empresaRepresentada"] = empresa

            key = _persona_key(rep2)
            existing = otorgantes_map.get(key)
            if existing:
                # Si ya existía sin empresa, le agregamos la empresa
                if not existing.get("empresaRepresentada"):
                    existing["empresaRepresentada"] = empresa
            else:
                otorgantes_map[key] = rep2

        otorgantes = list(otorgantes_map.values())

        # --- 3.3 Beneficiarios PN (DONATARIO) ---
        beneficiarios_map: dict[tuple, dict] = {}
        for p in ben_pn:
            p2 = _fix_persona_full(p)
            p2["rol"] = "DONATARIO"
            p2.setdefault("empresaRepresentada", None)
            p2["relacion"] = "TITULAR"  # Asumimos que son titulares si no tienen representante
            beneficiarios_map[_persona_key(p2)] = p2

        # --- 3.4 Beneficiarios PJ (si algún día los usas) ---
        for pj in ben_pj:
            pj_dict = dict(pj or {})
            rep = pj_dict.get("representante") or None
            if not rep:
                continue
            rep2 = _fix_persona_full(rep)
            rep2["rol"] = "DONATARIO"
            rep2["relacion"] = "REPRESENTANTE"  # Aquí indicamos que es un representante
            rep2.setdefault("empresaRepresentada", None)

            empresa = _build_empresa_from_pj(pj_dict)
            rep2["empresaRepresentada"] = empresa

            key = _persona_key(rep2)
            existing = beneficiarios_map.get(key)
            if existing:
                if not existing.get("empresaRepresentada"):
                    existing["empresaRepresentada"] = empresa
            else:
                beneficiarios_map[key] = rep2

        beneficiarios = list(beneficiarios_map.values())

        cleaned["otorgantes"] = otorgantes
        cleaned["beneficiarios"] = beneficiarios

        # Limpiamos claves intermedias que el modelo final no conoce
        for key in ("otorgantePN", "beneficiarioPN", "otorgantePJ", "beneficiarioPJ"):
            cleaned.pop(key, None)

    except Exception:
        # No romper el flujo si algo viene raro
        pass

    return DonacionResponse(**cleaned)

