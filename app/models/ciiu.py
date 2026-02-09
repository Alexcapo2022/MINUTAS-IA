# app/models/ciiu.py
from sqlalchemy import Column, String, DateTime, Integer
from app.db.base import Base


class Ciiu(Base):
    __tablename__ = "p_ciiu"

    co_ciiu = Column(Integer, primary_key=True)     # A, B, C...
    co_codigo = Column(String(1), nullable=False)        # CODIGO CIIU
    de_actividad = Column(String(255), nullable=False)
    in_estado = Column(Integer, nullable=False)        # 1 activo, 0 inactivo
    fe_creacion = Column(DateTime, nullable=False)  
