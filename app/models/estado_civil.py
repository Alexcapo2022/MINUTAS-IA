
from sqlalchemy import Column, String, Integer
from app.db.base import Base

class Estado_Civil(Base):
    __tablename__ = "a_tipo_estado_civil"

    co_tipo_estado_civil = Column(Integer, primary_key=True, autoincrement=True)     # S, C, D...
    no_tipo_estado_civil = Column(String(100), nullable=False)
    nc_tipo_estado_civil = Column(String(50), nullable=True)     # si en BD tiene default CURRENT_TIMESTAMP, puede ser nullable
    in_estado = Column(Integer, nullable=True)        # 1 activo, 0 inactivo