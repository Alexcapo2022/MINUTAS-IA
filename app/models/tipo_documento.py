



from sqlalchemy import Column, Integer, String
from app.db.base import Base


class Tipo_Documento(Base):
    __tablename__ = "a_tipo_documento"

    co_tipo_documento = Column(Integer, primary_key=True, autoincrement=True)     # CC, TI, CE...
    no_tipo_documento = Column(String(100), nullable=False)
    nc_tipo_documento = Column(String(50), nullable=False)
    in_estado = Column(Integer, nullable=True)        # 1 activo, 0 inactivo
    co_facturacion_electronica = Column(Integer, nullable=True)  
   
    