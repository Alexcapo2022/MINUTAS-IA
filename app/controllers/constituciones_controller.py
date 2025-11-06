from typing import List, Literal, Optional
from fastapi import UploadFile
from pydantic import BaseModel
from app.utils.ingestion import get_text_from_upload  # PDF/DOC/DOCX -> texto
from app.utils.gpt_client import extract_constitucion_text
from app.utils.parsing import normalize_payload

Moneda = Literal["PEN", "USD", "EUR"]
Rol = Literal["Titular", "Socio", "Accionista", "Transferente"]
TipoDoc = Literal["DNI", "CE", "PAS"]
TipoBien = Literal["Mueble", "Inmueble", "Dinero", "Otro"]
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
    domicilio: DomicilioObj = DomicilioObj()   # <<--- AHORA OBJETO
    porcentajeParticipacion: float = 0.0
    accionesSuscritas: int = 0
    montoAportado: float = 0.0
    rol: Literal["Titular","Socio","Accionista","Transferente"]

class Beneficiario(BaseModel):
    razonSocial: str = ""
    direccion: str = ""
    ubigeo: Ubigeo = Ubigeo()
    ciiu: List[str] = []  # solo descripciones

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

async def parse_constitucion(file: UploadFile) -> ConstitucionResponse:
    """
    Recibe PDF o Word (DOC/DOCX) y retorna el JSON estructurado.
    """
    texto = await get_text_from_upload(file)  # igual que poder: maneja PDF/DOC/DOCX
    raw = await extract_constitucion_text(contenido=texto, fecha_minuta_hint=None)
    cleaned = normalize_payload(raw)
    return ConstitucionResponse(**cleaned)
