# imports iguales...
from typing import List, Literal, Optional
from fastapi import UploadFile
from pydantic import BaseModel
from app.utils.ingestion import get_text_from_upload
from app.utils.gpt_client import extract_constitucion_text
from app.utils.parsing import normalize_payload

Moneda = Literal["PEN", "USD", "EUR"]
Rol = Literal["Titular", "Socio", "Accionista", "Transferente"]
TipoDoc = Literal["DNI", "CE", "PAS"]

# 👇 Ampliamos para permitir el default requerido
TipoBien = Literal["Mueble", "Inmueble", "Dinero", "Otro", "BIENES"]

MedioPago = Literal["Transferencia", "Cheque", "Depósito", "Efectivo", "Otro"]
FormaPago = Literal["Depósito", "Transferencia", "Efectivo", "Crédito", "Otro"]

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
    genero: Literal["MASCULINO", "FEMENINO"]            # <- agregado
    rol: Literal["Titular","Socio","Accionista","Transferente"]

class Beneficiario(BaseModel):
    razonSocial: str = ""
    direccion: str = ""
    ubigeo: Ubigeo = Ubigeo()
    # Ahora explicitar que guardaremos SOLO 1 categoría de la lista oficial
    ciiu: List[str] = []  # contendrá exactamente 1 ítem del catálogo oficial

class Transferencia(BaseModel):
    moneda: Moneda
    monto: float = 0.0
    formaPago: FormaPago
    oportunidadPago: str = ""

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
    moneda: Moneda = "PEN"
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

    # 🔹 nuevo campo:
    transferenciaTotal: float = 0.0

async def parse_constitucion(file: UploadFile) -> ConstitucionResponse:
    """
    Recibe PDF o Word (DOC/DOCX) y retorna el JSON estructurado.
    """
    texto = await get_text_from_upload(file)
    raw = await extract_constitucion_text(contenido=texto, fecha_minuta_hint=None)
    cleaned = normalize_payload(raw)

    # --- Blindajes mínimos ---

    # CIIU: garantizar exactamente 1 categoría si el modelo devolvió 0 o más de 1.
    # (El prompt ya obliga a 1, esto es sólo cinturón de seguridad)
    if "beneficiario" in cleaned:
        ciiu = (cleaned["beneficiario"] or {}).get("ciiu") or []
        if not isinstance(ciiu, list):
            ciiu = [str(ciiu)]
        if len(ciiu) == 0:
            # fallback neutro (elige una por defecto si el modelo no devolvió nada)
            ciiu = ["ACTIVIDADES INMOBILIARIAS, EMPRESARIALES Y DE ALQUILER"]
        else:
            ciiu = [str(ciiu[0])]
        cleaned["beneficiario"]["ciiu"] = ciiu

    # Bien: si está vacío o faltan campos, aplicar defaults requeridos
    b = cleaned.get("bien") or []
    if not b:
        b = [{
            "tipo": "BIENES",
            "clase": "OTROS NO ESPECIFICADOS",
            "otrosBienesNoEspecificados": "CAPITAL"
        }]
    else:
        # Completar faltantes en el primer bien
        b0 = dict(b[0])
        b0["tipo"] = b0.get("tipo") or "BIENES"
        b0["clase"] = b0.get("clase") or "OTROS NO ESPECIFICADOS"
        b0["otrosBienesNoEspecificados"] = b0.get("otrosBienesNoEspecificados") or "CAPITAL"
        b = [b0]
    cleaned["bien"] = b

    # --- total de transferencias (server-side) ---
    total = 0.0
    for t in cleaned.get("transferencia", []) or []:
        try:
            total += float(t.get("monto", 0) or 0)
        except Exception:
            pass
    cleaned["transferenciaTotal"] = round(total, 2)

    return ConstitucionResponse(**cleaned)
