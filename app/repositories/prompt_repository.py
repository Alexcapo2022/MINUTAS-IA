# app/repositories/prompt_repository.py
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.servicio_cnl import ServicioCnl
from app.models.prompt import Prompt
from app.models.servicio_cnl_prompt import ServicioCnlPrompt

class PromptRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_prompt_by_co_cnl(self, co_cnl: str) -> Prompt | None:
        """
        Devuelve el prompt activo asociado a un co_cnl (ej: '0101', '0604').
        Usa JOIN: servicio -> relacion -> prompt
        """
        stmt = (
            select(Prompt)
            .join(ServicioCnlPrompt, ServicioCnlPrompt.co_prompt == Prompt.co_prompt)
            .join(ServicioCnl, ServicioCnl.co_servicio_cnl == ServicioCnlPrompt.co_servicio_cnl)
            .where(ServicioCnl.co_cnl == co_cnl)
            .where(ServicioCnlPrompt.in_estado == 1)
            .where(Prompt.in_estado == 1)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def get_prompt_and_servicio_by_co_cnl(self, co_cnl: str) -> dict | None:
        """
        Retorna { prompt, de_servicio, servicio_obj } para un co_cnl.
        - servicio_obj: objeto ServicioCnl completo (con columnas de parametrización).
        """
        stmt = (
            select(Prompt, ServicioCnl)
            .join(ServicioCnlPrompt, ServicioCnlPrompt.co_prompt == Prompt.co_prompt)
            .join(ServicioCnl, ServicioCnl.co_servicio_cnl == ServicioCnlPrompt.co_servicio_cnl)
            .where(ServicioCnl.co_cnl == co_cnl)
            .where(ServicioCnlPrompt.in_estado == 1)
            .where(Prompt.in_estado == 1)
            .limit(1)
        )

        row = self.db.execute(stmt).first()
        if not row:
            return None

        prompt_obj, servicio_obj = row
        de_servicio = (getattr(servicio_obj, "de_servicio", None) or "").strip()

        return {
            "prompt": prompt_obj,
            "de_servicio": de_servicio,
            "servicio_obj": servicio_obj,   # ← objeto completo con cols de parametrización
        }

    def get_servicio_by_co_cnl(self, co_cnl: str) -> str:
        """
        Retorna ServicioCnl.de_servicio por co_cnl (solo activos en la relación).
        """
        stmt = (
            select(ServicioCnl.de_servicio)
            .join(ServicioCnlPrompt, ServicioCnlPrompt.co_servicio_cnl == ServicioCnl.co_servicio_cnl)
            .where(ServicioCnl.co_cnl == co_cnl)
            .where(ServicioCnlPrompt.in_estado == 1)
            .limit(1)
        )
        return (self.db.execute(stmt).scalar() or "").strip()
