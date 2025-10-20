from typing import Any, Dict, List
from pydantic import BaseModel, Field
from app.schemas.base import Persona, ExtractMapped
from app.utils.text import full_name

class WarningItem(BaseModel):
    code: str
    message: str

class ErrorItem(BaseModel):
    code: str
    message: str

class CompactPerson(BaseModel):
    nombre_completo: str = ""
    tipo_documento: str = ""
    numero_documento: str = ""
    direccion: str = ""

    @classmethod
    def from_person(cls, p: Persona, mask_fn=None):
        num = p.numero_documento
        if mask_fn:
            num = mask_fn(num)
        return cls(
            nombre_completo=full_name(p.nombres, p.apellido_paterno, p.apellido_materno),
            tipo_documento=p.tipo_documento,
            numero_documento=num,
            direccion=p.domicilio.direccion
        )

class ExtractOutCompact(BaseModel):
    acto: str = ""
    fecha_minuta: str = ""
    otorgantes: List[CompactPerson] = Field(default_factory=list)
    beneficiarios: List[CompactPerson] = Field(default_factory=list)
    confidence_overall: float = 0.0

    @classmethod
    def from_mapped(cls, mapped: ExtractMapped, mask_fn=None):
        return cls(
            acto=mapped.acto,
            fecha_minuta=mapped.fecha_minuta,
            otorgantes=[CompactPerson.from_person(p, mask_fn) for p in mapped.generales_ley.otorgantes],
            beneficiarios=[CompactPerson.from_person(p, mask_fn) for p in mapped.generales_ley.beneficiarios],
            confidence_overall=float(mapped.confidence.get("clasificacion_acto", 0.0))
        )

class ApiResponse(BaseModel):
    ok: bool = True
    meta: Dict[str, Any] = Field(default_factory=dict)
    view: str = "compact"
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[ErrorItem] = Field(default_factory=list)
    warnings: List[WarningItem] = Field(default_factory=list)

class SummaryPersona(BaseModel):
    nombres: str = ""
    apellido_paterno: str = ""
    apellido_materno: str = ""
    nacionalidad: str = ""
    tipo_documento: str = ""
    numero_documento: str = ""
    profesion_ocupacion: str = ""
    estado_civil: str = ""
    domicilio: dict = Field(
        default_factory=lambda: {
            "direccion": "",
            "distrito": "",
            "provincia": "",
            "departamento": "",
            "ubigeo": "",
        }
    )

class ExtractOutSummary(BaseModel):
    acto: str = "PODER"
    fecha_minuta: str = ""

    poderdantes_count: int = 0
    apoderados_count: int = 0

    poderdantes: List[SummaryPersona] = Field(default_factory=list)
    apoderados: List[SummaryPersona] = Field(default_factory=list)

    @classmethod
    def from_mapped(cls, mapped: ExtractMapped) -> "ExtractOutSummary":
        def asdict(obj: Any) -> Dict[str, Any]:
            if obj is None:
                return {}
            if isinstance(obj, BaseModel):  # Persona, Domicilio, etc. (Pydantic v2)
                return obj.model_dump()
            if isinstance(obj, dict):
                return obj
            # último recurso
            try:
                return dict(obj)
            except Exception:
                return {}

        def to_summary_person(p_obj: Any) -> SummaryPersona:
            p = asdict(p_obj)
            dom = asdict(p.get("domicilio", {}))
            dom_out = {
                "direccion": dom.get("direccion", "") or "",
                "distrito": dom.get("distrito", "") or "",
                "provincia": dom.get("provincia", "") or "",
                "departamento": dom.get("departamento", "") or "",
                "ubigeo": dom.get("ubigeo", "") or "",
            }
            return SummaryPersona(
                nombres=p.get("nombres", "") or "",
                apellido_paterno=p.get("apellido_paterno", "") or "",
                apellido_materno=p.get("apellido_materno", "") or "",
                nacionalidad=p.get("nacionalidad", "") or "",
                tipo_documento=p.get("tipo_documento", "") or "",
                numero_documento=p.get("numero_documento", "") or "",
                profesion_ocupacion=p.get("profesion_ocupacion", "") or "",
                estado_civil=p.get("estado_civil", "") or "",
                domicilio=dom_out,
            )

        # mapped.generales_ley.* pueden ser listas de Persona (BaseModel)
        otorgantes = [to_summary_person(p) for p in (mapped.generales_ley.otorgantes or [])]
        beneficiarios = [to_summary_person(p) for p in (mapped.generales_ley.beneficiarios or [])]

        return cls(
            acto=mapped.acto or "PODER",
            fecha_minuta=mapped.fecha_minuta or "",
            poderdantes_count=len(otorgantes),
            apoderados_count=len(beneficiarios),
            poderdantes=otorgantes,
            apoderados=beneficiarios,
        )