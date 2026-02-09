# app/schemas/payload_schemas.py
from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from app.schemas.enums import Genero, TipoPersona

# ======================
# Modelos base
# ======================
class Ubigeo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    departamento: str = ""
    provincia: str = ""
    distrito: str = ""
    
class Domicilio(BaseModel):
    model_config = ConfigDict(extra="ignore")
    direccion: str = ""
    ubigeo: Ubigeo = Field(default_factory=Ubigeo)

class Documento(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    co_documento: Optional[int] = None
    tipo_documento: str = Field(default="", alias="tipo_documento")    # DNI|CE|PAS|RUC|OTRO
    numero_documento: str = Field(default="", alias="numero_documento")

class Participante(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tipo_persona: TipoPersona = "NATURAL"
    nombres: str = ""
    apellido_paterno: str = ""
    apellido_materno: str = ""
    razon_social: str = ""
    ciiu: str = ""
    co_ciiu: Optional[int] = None

    pais: str = ""
    co_pais: Optional[int] = None

    documento: Documento = Field(default_factory=Documento)

    ocupacion: str = ""
    otros_ocupaciones: str = ""
    co_ocupacion: Optional[int] = None

    estado_civil: str = ""
    co_estado_civil: Optional[int] = None

    domicilio: Domicilio = Field(default_factory=Domicilio)
    genero: Genero = ""

    rol: str = ""
    relacion: str = ""

    porcentaje_participacion: float = 0.0
    numeroAcciones_participaciones: int = 0
    acciones_suscritas: int = 0
    monto_aportado: float = 0.0
    
class Transferencia(BaseModel):
    model_config = ConfigDict(extra="ignore")

    moneda: str = ""
    co_moneda: Optional[int] = None
    monto: float = 0.0
    forma_pago: str = ""
    oportunidad_pago: str = ""

class MedioPago(BaseModel):
    """
    Unión:
    - Donación/Constitución: valorBien
    - Base anterior: monto
    - CompraVenta: banco/cuenta/fecha/numeroDoc
    """
    model_config = ConfigDict(extra="ignore")
    medio_pago: str = ""
    moneda: str = ""
    co_moneda: Optional[int] = None
    valor_bien: float = 0.0
    fecha_pago: str = ""
    bancos: str = ""
    documento_pago: str = ""

class Bien(BaseModel):

    model_config = ConfigDict(extra="ignore")
    tipo_bien: str = ""
    clase_bien: str = ""
    ubigeo: Ubigeo = Field(default_factory=Ubigeo)
    partida_registral: str = ""
    zona_registral: str = ""
    co_zona_registral: Optional[int] = None
    fecha_adquisicion: str = ""
    fecha_minuta: str = "" ## FECHA DE ADQUISICION DE LA MINUTA DEL BIEN
    opcion_bien_mueble: str = ""
    numero_psm: str = "" # numero de placa, serie o motor
    otros_bienes: str = ""

class Acto(BaseModel):
    model_config = ConfigDict(extra="ignore")
    nombre_servicio: str = ""
    fecha_minuta: str = ""

class ParticipantesGroup(BaseModel):
    model_config = ConfigDict(extra="ignore")

    otorgantes: List[Participante] = Field(default_factory=list)
    beneficiarios: List[Participante] = Field(default_factory=list)


class ValoresGroup(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # En tus JSON actuales es lista, así debe quedar
    transferencia: List[Transferencia] = Field(default_factory=list)
    medioPago: List[MedioPago] = Field(default_factory=list)


# ======================
# Payload canónico FINAL
# ======================
class CanonicalPayload(BaseModel):

    model_config = ConfigDict(extra="ignore")
    acto: Acto = Field(default_factory=Acto)
    participantes: ParticipantesGroup = Field(default_factory=ParticipantesGroup)
    valores: ValoresGroup = Field(default_factory=ValoresGroup)
    bienes: List[Bien] = Field(default_factory=list)