# app/controllers/compraventa_controller.py
from typing import List, Literal, Optional
from fastapi import UploadFile
from pydantic import BaseModel

from app.utils.ingestion import get_text_from_upload
from app.utils.gpt_client import extract_compraventa_text
from app.utils.parsing import normalize_payload

# ============================
# Tipos y modelos
# ============================

Moneda = Literal["SOLES", "DOLARES AMERICANOS", "EUROS"]
TipoDoc = Literal["DNI", "CE", "PAS"]
MedioPagoEnum = Literal["Transferencia", "Cheque", "Depósito", "Efectivo", "Otro"]
TipoBien = Literal["Mueble", "Inmueble", "Dinero", "Otro", "BIENES"]

Genero = Literal["MASCULINO", "FEMENINO"]

class Ubigeo(BaseModel):
    departamento: str = ""
    provincia: str = ""
    distrito: str = ""

class DomicilioObj(BaseModel):
    direccion: str = ""
    ubigeo: Ubigeo = Ubigeo()

class DocumentoIdentidad(BaseModel):
    tipo: TipoDoc
    numero: str

class Parte(BaseModel):
    """
    Modela tanto al Otorgante como al Beneficiario de la compra-venta.
    """
    nombres: str = ""
    apellidoPaterno: str = ""
    apellidoMaterno: str = ""
    nacionalidad: str = ""
    documento: DocumentoIdentidad
    profesionOcupacion: str = ""
    estadoCivil: str = ""
    domicilio: DomicilioObj = DomicilioObj()
    genero: Genero

    # Estos dos campos están en tu layout de “Generales de Ley”,
    # si no aplican para la minuta concreta, irán como 0.
    porcentajeParticipacion: float = 0.0
    numeroAccionesParticipaciones: int = 0

class Transferencia(BaseModel):
    moneda: Moneda
    monto: float = 0.0
    formaPago: Literal["Contado", "Crédito", "Otro"] = "Contado"
    oportunidadPago: str = "A LA FIRMA DEL INSTRUMENTO PÚBLICO PROTOCOLAR"

class MedioPagoItem(BaseModel):
    medio: MedioPagoEnum
    moneda: Moneda
    valorBien: float = 0.0
    banco: str = ""
    cuentaBancaria: str = ""
    fechaDocumentoPago: str = ""   # YYYY-MM-DD o ""
    numeroDocumentoPago: str = ""

class Bien(BaseModel):
    tipo: TipoBien = "BIENES"
    clase: str = "PREDIOS"
    partidaRegistral: str = ""
    ubigeo: Ubigeo = Ubigeo()
    zonaRegistral: str = ""
    fechaMinuta: Optional[str] = None  # la misma o se puede recalcular

class CompraVentaResponse(BaseModel):
    tipoDocumento: Literal["Compra Venta"]
    fechaMinuta: Optional[str] = None

    otorgantes: List[Parte] = []
    beneficiarios: List[Parte] = []

    transferencia: List[Transferencia] = []
    medioPago: List[MedioPagoItem] = []
    bien: List[Bien] = []


# ============================
# Helpers de normalización
# ============================

def _norm_moneda(x: str) -> str:
    s = (x or "").strip().upper()
    if any(k in s for k in ["PEN", "SOL", "SOLES", "S/", "S/."]):
        return "SOLES"
    if any(k in s for k in ["USD", "US$", "USD$", "DOLAR", "DÓLAR", "DOLARES", "DÓLARES", "$"]):
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


# ============================
# Controller principal
# ============================

async def parse_compra_venta(file: UploadFile) -> CompraVentaResponse:
    """
    Recibe PDF o Word (DOC/DOCX) de una minuta de COMPRA-VENTA
    y retorna el JSON estructurado para alimentar tu tabla.
    """
    texto = await get_text_from_upload(file)
    raw = await extract_compraventa_text(contenido=texto, fecha_minuta_hint=None)
    cleaned = normalize_payload(raw)

    # --- Normalizar medioPago + transferencia (muy similar a constitución) ---
    raw_medio = cleaned.get("medioPago") or []
    raw_trans = cleaned.get("transferencia") or []

    # Si no hay medioPago pero sí transferencia, migramos
    if not raw_medio and raw_trans:
        raw_medio = [{
            "medio": _map_forma_to_medio(t.get("formaPago", "")),
            "moneda": _norm_moneda(t.get("moneda") or "SOLES"),
            "valorBien": float(t.get("monto") or 0.0),
            "banco": t.get("banco") or "",
            "cuentaBancaria": t.get("cuentaBancaria") or "",
            "fechaDocumentoPago": t.get("fechaDocumentoPago") or "",
            "numeroDocumentoPago": t.get("numeroDocumentoPago") or "",
        } for t in raw_trans]

    medio_pago = [{
        "medio": (m.get("medio") or "Otro"),
        "moneda": _norm_moneda(m.get("moneda") or "SOLES"),
        "valorBien": float(m.get("valorBien") or 0.0),
        "banco": m.get("banco") or "",
        "cuentaBancaria": m.get("cuentaBancaria") or "",
        "fechaDocumentoPago": m.get("fechaDocumentoPago") or "",
        "numeroDocumentoPago": m.get("numeroDocumentoPago") or "",
    } for m in raw_medio]

    total = round(sum(m["valorBien"] for m in medio_pago), 2)
    moneda_base = medio_pago[0]["moneda"] if medio_pago else "SOLES"

    cleaned["medioPago"] = medio_pago
    cleaned["transferencia"] = [{
        "moneda": moneda_base,
        "monto": total,
        "formaPago": "Contado",
        "oportunidadPago": "A LA FIRMA DEL INSTRUMENTO PÚBLICO PROTOCOLAR",
    }]

    # --- BIEN: defaults acordes a tu layout ---
    b = cleaned.get("bien") or []
    if b:
        b0 = dict(b[0])
        cleaned["bien"] = [{
            "tipo": b0.get("tipo") or "BIENES",
            "clase": b0.get("clase") or "PREDIOS",
            "partidaRegistral": b0.get("partidaRegistral") or "",
            "ubigeo": b0.get("ubigeo") or {},
            "zonaRegistral": b0.get("zonaRegistral") or "",
            "fechaMinuta": cleaned.get("fechaMinuta"),
        }]
    else:
        cleaned["bien"] = [{
            "tipo": "BIENES",
            "clase": "PREDIOS",
            "partidaRegistral": "",
            "ubigeo": {},
            "zonaRegistral": "",
            "fechaMinuta": cleaned.get("fechaMinuta"),
        }]

    # Regla extra: si hay departamento y zonaRegistral está vacía, usar el departamento
    try:
        bien_list = cleaned.get("bien") or []
        if bien_list:
            bien0 = dict(bien_list[0])
            ubi = (bien0.get("ubigeo") or {}) or {}
            departamento = (ubi.get("departamento") or "").strip()
            zona = (bien0.get("zonaRegistral") or "").strip()

            if departamento and not zona:
                bien0["zonaRegistral"] = departamento

            cleaned["bien"][0] = bien0
    except Exception:
        # No rompemos el flujo si viene algo raro en bien/ubigeo
        pass

    # --- Inferir nacionalidad PERUANA cuando esté vacía ---
    try:
        def _fix_nat(persona: dict) -> dict:
            nac = (persona.get("nacionalidad") or "").strip()
            if nac:
                return persona

            doc = (persona.get("documento") or {}) or {}
            tipo_doc = (doc.get("tipo") or "").upper()
            dom = (persona.get("domicilio") or {}) or {}
            ubi = (dom.get("ubigeo") or {}) or {}
            departamento = (ubi.get("departamento") or "").strip()

            # Criterio simple:
            # si tiene DNI y un departamento peruano informado, asumimos nacionalidad PERUANA
            if tipo_doc == "DNI" and departamento:
                persona["nacionalidad"] = "PERUANA"

            return persona

        otorg = cleaned.get("otorgantes") or []
        cleaned["otorgantes"] = [_fix_nat(dict(p)) for p in otorg]

        benef = cleaned.get("beneficiarios") or []
        cleaned["beneficiarios"] = [_fix_nat(dict(p)) for p in benef]
    except Exception:
        # Si algo viene mal estructurado, no reventamos la respuesta
        pass

    return CompraVentaResponse(**cleaned)
