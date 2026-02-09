


from app.db.base import Base
from sqlalchemy import Column, Integer, String


class Pais(Base):
    __tablename__ = "a_pais"

    co_pais = Column(Integer, primary_key=True, autoincrement=True)     # CODIGO PAIS
    co_uif = Column(Integer, nullable=False)        # CODIGO UIF
    no_pais = Column(String(200), nullable=False)
    gerundio_pais = Column(String(200), nullable=False) 
    in_estado = Column(Integer, nullable=True)        # 1 activo, 0 inactivo