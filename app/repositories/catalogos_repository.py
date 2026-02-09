# app/repositories/catalogos_repository.py
from sqlalchemy import and_, select, func
from sqlalchemy.orm import Session
from app.models.pais import Pais
from app.models.tipo_documento import Tipo_Documento
from app.models.ocupacion import Ocupacion
from app.models.estado_civil import Estado_Civil
from app.models.tipo_moneda import Tipo_moneda
from app.models.zona_registral import ZonaRegistral
import re

def _norm(s: str) -> str:
    return (s or "").strip().upper()

_STOPWORDS = {"DE", "DEL", "LA", "LAS", "EL", "LOS", "Y", "E", "EN", "A", "AL", "POR", "PARA"}


def _tokens(desc: str) -> list[str]:
    """
    "COMERCIANTE / VENDEDOR" -> ["COMERCIANTE", "VENDEDOR"]
    "TRADUCTORA" -> ["TRADUCTORA"]
    """
    s = _norm(desc)
    if not s:
        return []
    s = re.sub(r"[^A-Z0-9\s]", " ", s)  # quita símbolos
    s = re.sub(r"\s+", " ", s).strip()
    toks = [t for t in s.split(" ") if len(t) >= 3 and t not in _STOPWORDS]

    seen = set()
    out = []
    for t in toks:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out


class PaisRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_name(self, nombre: str) -> Pais | None:
        n = _norm(nombre)
        if not n:
            return None
        stmt = select(Pais).where(func.upper(Pais.no_pais) == n).where(Pais.in_estado == 1).limit(1)
        return self.db.execute(stmt).scalars().first()

class TipoDocumentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_nc(self, nc: str) -> Tipo_Documento | None:
        n = _norm(nc)
        if not n:
            return None
        stmt = select(Tipo_Documento).where(func.upper(Tipo_Documento.nc_tipo_documento) == n).where(Tipo_Documento.in_estado == 1).limit(1)
        return self.db.execute(stmt).scalars().first()

class OcupacionRepository:
    """
    Estrategia:
      1) Exact match: UPPER(de_ocupacion) == UPPER(desc)
      2) Token match: cada token debe aparecer dentro de de_ocupacion (LIKE %TOKEN%)
      3) Fallback: OTROS (Especificar)
    """
    def __init__(self, db: Session):
        self.db = db

    def find_by_desc(self, desc: str) -> Ocupacion | None:
        """
        Este método reemplaza al anterior para que normalize_payload siga llamando
        ocup_repo.find_by_desc(desc) sin cambiar nada en tu service.
        """
        if not (desc or "").strip():
            return None

        # 1) EXACT
        n = _norm(desc)
        stmt = (
            select(Ocupacion)
            .where(func.upper(Ocupacion.de_ocupacion) == n)
            .where(Ocupacion.in_estado == 1)
            .limit(1)
        )
        hit = self.db.execute(stmt).scalars().first()
        if hit:
            return hit

        # 2) TOKENS / LIKE (tolerante)
        toks = _tokens(desc)
        if toks:
            conds = [func.upper(Ocupacion.de_ocupacion).like(f"%{t}%") for t in toks]

            stmt = (
                select(Ocupacion)
                .where(and_(*conds))
                .where(Ocupacion.in_estado == 1)
                .order_by(func.length(Ocupacion.de_ocupacion).asc())
                .limit(1)
            )
            hit = self.db.execute(stmt).scalars().first()
            if hit:
                return hit

        # 3) FALLBACK: OTROS (Especificar) (en tu catálogo: 116)
        stmt = (
            select(Ocupacion)
            .where(func.upper(Ocupacion.de_ocupacion) == "OTROS (ESPECIFICAR)")
            .where(Ocupacion.in_estado == 1)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

class EstadoCivilRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_name(self, nombre: str) -> Estado_Civil | None:
        n = _norm(nombre)
        if not n:
            return None
        stmt = select(Estado_Civil).where(func.upper(Estado_Civil.no_tipo_estado_civil) == n).where(Estado_Civil.in_estado == 1).limit(1)
        return self.db.execute(stmt).scalars().first()

class MonedaRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_name(self, nombre: str) -> Tipo_moneda | None:
        n = _norm(nombre)
        if not n:
            return None
        stmt = select(Tipo_moneda).where(func.upper(Tipo_moneda.no_tipo_moneda) == n).where(Tipo_moneda.in_estado == 1).limit(1)
        return self.db.execute(stmt).scalars().first()
    
class ZonaRegistralRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_name(self, nombre: str) -> ZonaRegistral | None:
        n = _norm(nombre)
        if not n:
            return None
        stmt = (
            select(ZonaRegistral)
            .where(func.upper(ZonaRegistral.no_zona_registral) == n)
            .where(ZonaRegistral.in_estado == 1)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def find_by_nc(self, nc: str) -> ZonaRegistral | None:
        n = _norm(nc)
        if not n:
            return None
        stmt = (
            select(ZonaRegistral)
            .where(func.upper(ZonaRegistral.nc_zona_registral) == n)
            .where(ZonaRegistral.in_estado == 1)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def find_by_name_or_nc(self, value: str) -> ZonaRegistral | None:

        n = _norm(value)
        if not n:
            return None

        # 1) primero intenta por nc (normalmente es el caso 'LIMA', 'CUSCO', etc.)
        row = self.find_by_nc(n)
        if row:
            return row

        # 2) fallback por nombre completo
        return self.find_by_name(n)

