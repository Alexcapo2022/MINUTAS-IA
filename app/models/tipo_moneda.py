from sqlalchemy import Column, Integer,String
from app.db.base import Base


class Tipo_moneda(Base):
    __tablename__ = "a_tipo_moneda"
    
    co_tipo_moneda = Column(Integer, primary_key=True, autoincrement=True)     # CODIGO TIPO MONEDA
    no_tipo_moneda = Column(String(100), nullable=False)
    no_simbolo = Column(String(50), nullable=False)
    in_estado = Column(Integer, nullable=True)        # 1 activo, 0 inactivo