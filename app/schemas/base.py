# app/schemas/base.py
from typing import Dict, List
from pydantic import BaseModel, Field

class EvidenceItem(BaseModel):
    evidence_text: str = ""
    char_span: List[int] = Field(default_factory=list)

class Domicilio(BaseModel):
    direccion: str = ""
    ubigeo: str = ""
    distrito: str = ""
    provincia: str = ""
    departamento: str = ""

class DocumentoAdicional(BaseModel):
    tipo: str = ""
    numero: str = ""
    observaciones: str = ""

class Persona(BaseModel):
    nombres: str = ""
    apellido_paterno: str = ""
    apellido_materno: str = ""
    nacionalidad: str = ""
    tipo_documento: str = ""
    numero_documento: str = ""
    docs_adicionales: List[DocumentoAdicional] = Field(default_factory=list)
    profesion_ocupacion: str = ""
    estado_civil: str = ""
    domicilio: Domicilio = Domicilio()
    role: str = ""  # otorgante | beneficiario | indeterminado | ""
    evidence: Dict[str, EvidenceItem] = Field(default_factory=dict)

class GeneralesLey(BaseModel):
    otorgantes: List[Persona] = Field(default_factory=list)
    beneficiarios: List[Persona] = Field(default_factory=list)
    indeterminados: List[Persona] = Field(default_factory=list)

# NUEVO: modelo para confidence
class Confidence(BaseModel):
    clasificacion_acto: float = 0.0
    campos: Dict[str, float] = Field(default_factory=dict)

class ExtractMapped(BaseModel):
    acto: str = "PODER"
    generales_ley: GeneralesLey = GeneralesLey()
    fecha_minuta: str = ""
    confidence: Confidence = Confidence()   # <-- AQUÍ cambia
    raw_text_hash: str = ""

class ExtractOutFull(BaseModel):
    ok: bool
    filename: str
    extension: str
    pages: int
    bytes_size: int
    text_preview: str
    text_hash_sha256: str
    is_poder_guess: float
    mapped: ExtractMapped
