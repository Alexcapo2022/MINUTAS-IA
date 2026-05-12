from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, Text, ForeignKey, JSON
from datetime import datetime
from app.db.base import Base

class TipoDocumentoEscaneo(Base):
    __tablename__ = 'a_tipo_documento_escaneo'
    
    co_tipo_doc = Column(Integer, primary_key=True, autoincrement=True)
    de_tipo_doc = Column(String(50), nullable=False)
    in_estado = Column(Integer, default=1)

class EscaneoMedioPago(Base):
    __tablename__ = 'h_escaneo_medio_pago'
    
    id_escaneo = Column(Integer, primary_key=True, autoincrement=True)
    notaria = Column(String(255), nullable=False)
    co_tipo_doc = Column(Integer, ForeignKey('a_tipo_documento_escaneo.co_tipo_doc'), nullable=False)
    url_imagen = Column(String(255), nullable=False)
    referencia = Column(String(200), nullable=True)
    
    # Campos detectados
    medio_pago = Column(String(100), nullable=True)
    moneda = Column(String(20), nullable=True)
    monto = Column(Numeric(12, 2), nullable=True)
    fecha_pago = Column(Date, nullable=True)
    bancos = Column(String(100), nullable=True)
    documento_pago = Column(String(100), nullable=True)
    
    raw_ai_response = Column(JSON, nullable=True)
    ts_creacion = Column(DateTime, default=datetime.utcnow)

class AuditoriaEscaneo(Base):
    __tablename__ = 'a_auditoria_escaneo'
    
    id_auditoria = Column(Integer, primary_key=True, autoincrement=True)
    id_escaneo = Column(Integer, ForeignKey('h_escaneo_medio_pago.id_escaneo'), nullable=False)
    notaria = Column(String(255), nullable=False)
    duracion_ms = Column(Integer, nullable=True)
    tokens_consumidos = Column(Integer, nullable=True)
    estado = Column(String(20), nullable=False) # SUCCESS, ERROR
    mensaje_error = Column(Text, nullable=True)
    ts_ejecucion = Column(DateTime, default=datetime.utcnow)
