from sqlalchemy import Column, Integer, Integer, String
from app.db.base import Base

class ZonaRegistral(Base):
    __tablename__ = "a_zona_registral"

    co_zona_registral = Column(Integer, primary_key=True, autoincrement=True)  # CODIGO ZONA REGISTRAL
    no_zona_registral = Column(String(100), nullable=False)
    nc_zona_registral = Column(String(50), nullable=False)
    in_estado = Column(Integer, nullable=True)        # 1 activo, 0 inactivo