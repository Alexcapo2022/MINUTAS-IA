# app/repositories/ciiu_repository.py
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.ciiu import Ciiu

class CiiuRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_activos(self) -> list[Ciiu]:
        stmt = select(Ciiu).where(Ciiu.in_estado == 1).order_by(Ciiu.co_ciiu.asc())
        return list(self.db.execute(stmt).scalars().all())

    def format_catalogo_for_prompt(self) -> str:
        rows = self.list_activos()
        # Ejemplo: "- A: AGRICULTURA...\n- B: PESCA..."
        return "\n".join([f"- {r.co_ciiu}: {r.de_actividad}" for r in rows])

    def find_by_codigo(self, codigo: str) -> Ciiu | None:
        if not codigo:
            return None
        stmt = select(Ciiu).where(Ciiu.co_ciiu == codigo.strip()).where(Ciiu.in_estado == 1).limit(1)
        return self.db.execute(stmt).scalars().first()

    def find_by_actividad_exacta(self, actividad: str) -> Ciiu | None:
        if not actividad:
            return None
        stmt = (
            select(Ciiu)
            .where(Ciiu.de_actividad == actividad.strip())
            .where(Ciiu.in_estado == 1)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def find_best_match(self, value: str) -> Ciiu | None:
        """
        Soporta:
        - "A"
        - "CONSTRUCCION"
        - "F: CONSTRUCCION"
        - "F - CONSTRUCCION"
        """
        if not value:
            return None

        s = value.strip()

        # Caso 1: viene solo letra
        if len(s) <= 3 and s[0].isalpha():
            row = self.find_by_codigo(s[0].upper())
            if row:
                return row

        # Caso 2: viene "X: ACTIVIDAD" o "X - ACTIVIDAD"
        for sep in [":", "-", "—"]:
            if sep in s:
                left, right = s.split(sep, 1)
                left = left.strip()
                right = right.strip()

                if left and len(left) <= 3 and left[0].isalpha():
                    row = self.find_by_codigo(left[0].upper())
                    if row:
                        return row

                # si no calza por código, probamos por actividad
                row = self.find_by_actividad_exacta(right)
                if row:
                    return row

        # Caso 3: viene solo actividad
        row = self.find_by_actividad_exacta(s)
        if row:
            return row

        # Fallback: LIKE (simple)
        stmt = (
            select(Ciiu)
            .where(Ciiu.de_actividad.ilike(f"%{s}%"))
            .where(Ciiu.in_estado == 1)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()
