# imports iguales...
from typing import List, Literal, Optional
from fastapi import UploadFile
from pydantic import BaseModel
from app.utils.ingestion import get_text_from_upload
from app.utils.gpt_client import extract_constitucion_text
from app.utils.parsing import normalize_payload

# ============================
# Tipos y modelos
# ============================

Moneda = Literal["SOLES", "DOLARES AMERICANOS", "EUROS"]
Rol = Literal["Titular", "Socio", "Accionista", "Transferente"]
TipoDoc = Literal["DNI", "CE", "PAS"]
TipoBien = Literal["Mueble", "Inmueble", "Dinero", "Otro", "BIENES"]

MedioPago = Literal["Transferencia", "Cheque", "Depósito", "Efectivo", "Otro"]
# Agregamos "Contado" como forma de pago válida (aunque transferencia única lo usará por defecto)
FormaPago = Literal["Depósito", "Transferencia", "Efectivo", "Crédito", "Otro", "Contado"]

class Ubigeo(BaseModel):
    departamento: str = ""
    provincia: str = ""
    distrito: str = ""

class DomicilioObj(BaseModel):
    direccion: str = ""
    ubigeo: Ubigeo = Ubigeo()

class DocumentoIdentidad(BaseModel):
    tipo: Literal["DNI", "CE", "PAS"]
    numero: str

class Otorgante(BaseModel):
    nombres: str = ""
    apellidoPaterno: str = ""
    apellidoMaterno: str = ""
    documento: DocumentoIdentidad
    nacionalidad: str = ""
    estadoCivil: str = ""
    domicilio: DomicilioObj = DomicilioObj()
    porcentajeParticipacion: float = 0.0
    accionesSuscritas: int = 0
    montoAportado: float = 0.0
    genero: Literal["MASCULINO", "FEMENINO"]
    rol: Literal["Titular","Socio","Accionista","Transferente"]

class Beneficiario(BaseModel):
    razonSocial: str = ""
    direccion: str = ""
    ubigeo: Ubigeo = Ubigeo()
    # Guardaremos EXACTAMENTE 1 categoría del catálogo (el prompt ya lo fuerza; aquí blindamos)
    ciiu: List[str] = []

class Transferencia(BaseModel):
    moneda: Moneda
    monto: float = 0.0
    # Defaults exigidos
    formaPago: FormaPago = "Contado"
    oportunidadPago: str = "A LA FIRMA DEL INSTRUMENTO PÚBLICO PROTOCOLAR"

class MedioPagoItem(BaseModel):
    medio: MedioPago
    moneda: Moneda
    valorBien: float = 0.0

class Bien(BaseModel):
    tipo: TipoBien
    clase: str = ""
    otrosBienesNoEspecificados: str = ""

class CapitalSocial(BaseModel):
    monto: float = 0.0
    moneda: Moneda = "SOLES"
    accionesTotales: int = 0

class ConstitucionResponse(BaseModel):
    tipoDocumento: Literal["Constitución de Empresa"]
    tipoSociedad: Literal["EIRL", "SRL", "SAC", "SA", "Otra"]
    fechaMinuta: Optional[str] = None

    otorgantes: List[Otorgante] = []
    beneficiario: Beneficiario

    transferencia: List[Transferencia] = []
    medioPago: List[MedioPagoItem] = []
    bien: List[Bien] = []


# ============================
# Helpers de normalización
# ============================

def _norm_moneda(x: str) -> str:
    s = (x or "").strip().upper()
    # SOLES
    if any(k in s for k in ["PEN", "SOL", "SOLES", "S/", "S/."]):
        return "SOLES"
    # DÓLARES
    if any(k in s for k in ["USD", "US$", "USD$", "DOLAR", "DÓLAR", "DOLARES", "DÓLARES", "$"]):
        return "DOLARES AMERICANOS"
    # EUROS
    if any(k in s for k in ["EUR", "€", "EURO", "EUROS"]):
        return "EUROS"
    # Fallback razonable
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


# ============================
# Controller principal
# ============================

async def parse_constitucion(file: UploadFile) -> ConstitucionResponse:
    """
    Recibe PDF o Word (DOC/DOCX) y retorna el JSON estructurado.
    """
    texto = await get_text_from_upload(file)
    raw = await extract_constitucion_text(contenido=texto, fecha_minuta_hint=None)
    cleaned = normalize_payload(raw)

    # --- CIIU: garantizar exactamente 1 categoría ---
    if "beneficiario" in cleaned:
        ciiu = (cleaned["beneficiario"] or {}).get("ciiu") or []
        if not isinstance(ciiu, list):
            ciiu = [str(ciiu)]
        cleaned["beneficiario"]["ciiu"] = [str(ciiu[0])] if ciiu else ["ACTIVIDADES INMOBILIARIAS, EMPRESARIALES Y DE ALQUILER"]

    # --- BIEN: defaults requeridos si falta info ---
    b = cleaned.get("bien") or []
    if b:
        b0 = dict(b[0])
        cleaned["bien"] = [{
            "tipo": b0.get("tipo") or "BIENES",
            "clase": b0.get("clase") or "OTROS NO ESPECIFICADOS",
            "otrosBienesNoEspecificados": b0.get("otrosBienesNoEspecificados") or "CAPITAL"
        }]
    else:
        cleaned["bien"] = [{
            "tipo": "BIENES",
            "clase": "OTROS NO ESPECIFICADOS",
            "otrosBienesNoEspecificados": "CAPITAL"
        }]

    # --- medioPago + transferencia única (una sola pasada) ---
    raw_medio: List[dict] = cleaned.get("medioPago") or []
    raw_trans: List[dict] = cleaned.get("transferencia") or []

    if not raw_medio and raw_trans:
        # migrar de transferencia → medioPago
        raw_medio = [{
            "medio": _map_forma_to_medio(t.get("formaPago", "")),
            "moneda": _norm_moneda(t.get("moneda") or "SOLES"),
            "valorBien": float(t.get("monto") or 0.0),
        } for t in raw_trans]

    # normalizar medioPago (moneda y valor)
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
        "formaPago": "Contado",
        "oportunidadPago": "A LA FIRMA DEL INSTRUMENTO PÚBLICO PROTOCOLAR"
    }]

    # --- CapitalSocial (si existe): normaliza moneda una sola vez ---
    if isinstance(cleaned.get("capitalSocial"), dict):
        cs = dict(cleaned["capitalSocial"])
        cs["moneda"] = _norm_moneda(cs.get("moneda") or "SOLES")
        cleaned["capitalSocial"] = cs

    # === NUEVO: Beneficiario.direccion (override) y ubigeo (relleno) desde el primer otorgante ===
    try:
        ben = cleaned.get("beneficiario") or {}
        ogts = cleaned.get("otorgantes") or []
        if ogts:
            first = ogts[0] or {}
            dom = (first.get("domicilio") or {})
            dir_ot = (dom.get("direccion") or "").strip()
            ubi_ot = (dom.get("ubigeo") or {}) or {}

            # Dirección: SIEMPRE usar la del primer otorgante si existe (override)
            if dir_ot:
                ben["direccion"] = dir_ot

            # Ubigeo: completar solo campos vacíos con valores del primer otorgante
            ben_ubi = (ben.get("ubigeo") or {}) or {}
            for k in ("departamento", "provincia", "distrito"):
                val_ot = (ubi_ot.get(k) or "").strip()
                if val_ot and (ben_ubi.get(k) or "").strip() == "":
                    ben_ubi[k] = val_ot

            ben["ubigeo"] = ben_ubi
            cleaned["beneficiario"] = ben
    except Exception:
        # No bloquear flujo si la estructura viene incompleta
        pass

    return ConstitucionResponse(**cleaned)
