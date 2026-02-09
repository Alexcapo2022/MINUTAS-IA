


from tokenize import String
from sqlalchemy import Column, Integer, String, DateTime
from app.db.base import Base


class Ocupacion(Base):
    __tablename__ = "a_ocupacion"

    co_ocupacion = Column(Integer, primary_key=True, autoincrement=True)     # CODIGO OCUPACION
    de_ocupacion = Column(String(180), nullable=False)
    co_uif = Column(String(3), nullable=False)
    co_modi_tabla = Column(Integer, nullable=False)  
    fe_modi_tabla = Column(DateTime, nullable=True)
    in_estado = Column(Integer, nullable=True)        # 1 activo, 0 inactivo