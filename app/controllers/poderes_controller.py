from typing import List, Literal, Optional
from fastapi import UploadFile
from pydantic import BaseModel
from app.utils.ingestion import get_text_from_upload
from app.utils.gpt_client import extract_poder_text
from app.utils.parsing import normalize_payload

# ==== MODELOS DE RESPUESTA ====

# ...tus imports
from pydantic import BaseModel
from typing import List, Literal, Optional

class Ubigeo(BaseModel):
    distrito: str = ""
    provincia: str = ""
    departamento: str = ""

class Domicilio(BaseModel):
    direccion: str = ""
    ubigeo: Ubigeo = Ubigeo()

class Persona(BaseModel):
    nombres: str = ""
    apellidoPaterno: str = ""
    apellidoMaterno: str = ""
    nacionalidad: str = ""
    tipoDocumento: str = ""
    numeroDocumento: str = ""
    profesionOcupacion: str = ""
    estadoCivil: str = ""
    domicilio: Domicilio = Domicilio()
    genero: Literal["MASCULINO", "FEMENINO"]  # <- NUEVO
    rol: Literal["PODERDANTE","APODERADO"]

class PoderResponse(BaseModel):
    tipoMinuta: Literal["PODER"]
    fechaMinuta: Optional[str] = None
    otorgantes: List[Persona]
    beneficiarios: List[Persona]


# ==== FUNCIÓN PRINCIPAL ====

async def parse_poder(file: UploadFile) -> PoderResponse:
    """
    Recibe un archivo (PDF o Word) y retorna el JSON estructurado.
    - Solo admite: application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document, application/msword
    """
    # 1) Extraer texto del archivo subido
    texto = await get_text_from_upload(file)

    # 2) Llamar a GPT con el texto
    raw = await extract_poder_text(contenido=texto, fecha_minuta_hint=None)

    # 3) Normalizaciones mínimas y validación final
    cleaned = normalize_payload(raw)
    return PoderResponse(**cleaned)
