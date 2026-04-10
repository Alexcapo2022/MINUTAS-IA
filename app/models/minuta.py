from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, Text, ForeignKey, Float
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class ConsultaMinuta(Base):
    """
    Tabla principal histórica de consultas de minutas procesadas.
    """
    __tablename__ = "p_consulta_minuta"

    id_consulta = Column(Integer, primary_key=True, autoincrement=True)
    co_cnl = Column(String(4), nullable=True)
    no_servicio = Column(String(255), nullable=True) # Acto.nombre_servicio
    fe_minuta = Column(Date, nullable=True)         # Acto.fecha_minuta
    minuta_archivo = Column(LONGBLOB, nullable=True) # Archivo DOCX en binario
    estado_minuta = Column(String(50), nullable=True) # EXITO / ERROR / PROCESANDO
    fe_creacion = Column(DateTime, default=datetime.now)

    # Relaciones
    participantes = relationship("ParticipanteMinuta", back_populates="consulta", cascade="all, delete-orphan")
    valores = relationship("ValorMinuta", back_populates="consulta", cascade="all, delete-orphan")
    bienes = relationship("BienMinuta", back_populates="consulta", cascade="all, delete-orphan")

class ParticipanteMinuta(Base):
    """
    Tabla auxiliar para almacenar los participantes extraídos de la minuta.
    Mapeado desde CanonicalPayload.participantes (otorgantes, beneficiarios, fiduciarios).
    """
    __tablename__ = "a_participante_minuta"

    id_participante = Column(Integer, primary_key=True, autoincrement=True)
    id_consulta = Column(Integer, ForeignKey("p_consulta_minuta.id_consulta"), nullable=False)
    
    grupo_participante = Column(String(20), nullable=True) # OTORGANTE, BENEFICIARIO, FIDUCIARIO
    tipo_persona = Column(String(20), nullable=True)       # NATURAL, JURIDICA
    
    # Datos Personales / Razón Social
    nombres = Column(String(100), nullable=True)
    apellido_paterno = Column(String(100), nullable=True)
    apellido_materno = Column(String(100), nullable=True)
    razon_social = Column(String(255), nullable=True)
    
    # Actividad Económica
    ciiu = Column(String(20), nullable=True)
    co_ciiu = Column(Integer, nullable=True)
    objeto_empresa = Column(Text, nullable=True)
    
    # Origen
    pais = Column(String(100), nullable=True)
    co_pais = Column(Integer, nullable=True)
    
    # Documento de Identidad (Aplanado)
    documento_tipo = Column(String(20), nullable=True)
    documento_numero = Column(String(20), nullable=True)
    documento_co = Column(Integer, nullable=True)
    
    # Ocupación y Estado Civil
    ocupacion = Column(String(100), nullable=True)
    co_ocupacion = Column(Integer, nullable=True)
    otros_ocupaciones = Column(Text, nullable=True)
    estado_civil = Column(String(50), nullable=True)
    co_estado_civil = Column(Integer, nullable=True)
    
    # Domicilio (Aplanado)
    domicilio_direccion = Column(String(255), nullable=True)
    ubigeo_departamento = Column(String(100), nullable=True)
    ubigeo_provincia = Column(String(100), nullable=True)
    ubigeo_distrito = Column(String(100), nullable=True)
    
    # Otros
    genero = Column(String(20), nullable=True)
    rol = Column(String(50), nullable=True)
    relacion = Column(String(50), nullable=True)
    
    # Datos Financieros / Participación
    porcentaje_participacion = Column(Float, default=0.0)
    nu_acciones = Column(Integer, default=0)
    nu_acciones_suscritas = Column(Integer, default=0)
    mo_aportado = Column(Float, default=0.0)

    # Relación back
    consulta = relationship("ConsultaMinuta", back_populates="participantes")

class ValorMinuta(Base):
    """
    Tabla auxiliar para almacenar valores (Transferencias y Medios de Pago).
    Mapeado desde CanonicalPayload.valores.
    """
    __tablename__ = "a_valores_minuta"

    id_valor = Column(Integer, primary_key=True, autoincrement=True)
    id_consulta = Column(Integer, ForeignKey("p_consulta_minuta.id_consulta"), nullable=False)
    
    tipo_valor = Column(String(20), nullable=True) # TRANSFERENCIA, MEDIO_PAGO
    
    # Común
    moneda = Column(String(10), nullable=True)
    co_moneda = Column(Integer, nullable=True)
    monto = Column(Numeric(18, 2), nullable=True)
    
    # Específico Transferencia
    forma_pago = Column(String(100), nullable=True)
    oportunidad_pago = Column(String(100), nullable=True)
    
    # Específico Medio Pago
    medio_pago_nombre = Column(String(100), nullable=True) # campo medio_pago
    valor_bien = Column(Numeric(18, 2), nullable=True)
    fecha_pago = Column(Date, nullable=True)
    bancos = Column(String(100), nullable=True)
    documento_pago = Column(String(100), nullable=True)

    # Relación back
    consulta = relationship("ConsultaMinuta", back_populates="valores")

class BienMinuta(Base):
    """
    Tabla auxiliar para almacenar los bienes extraídos.
    Mapeado desde CanonicalPayload.bienes.
    """
    __tablename__ = "a_bienes_minutas"

    id_bien = Column(Integer, primary_key=True, autoincrement=True)
    id_consulta = Column(Integer, ForeignKey("p_consulta_minuta.id_consulta"), nullable=False)
    
    tipo_bien = Column(String(100), nullable=True)
    clase_bien = Column(String(100), nullable=True)
    
    # Ubigeo
    ubigeo_departamento = Column(String(100), nullable=True)
    ubigeo_provincia = Column(String(100), nullable=True)
    ubigeo_distrito = Column(String(100), nullable=True)
    
    # Registros
    partida_registral = Column(String(50), nullable=True)
    zona_registral = Column(String(100), nullable=True)
    co_zona_registral = Column(String(10), nullable=True)
    
    # Fechas
    fe_adquisicion = Column(Date, nullable=True)
    fe_minuta_bien = Column(Date, nullable=True)
    
    # Datos Vehículos / Otros
    opcion_bien_mueble = Column(String(100), nullable=True)
    nu_psm = Column(String(100), nullable=True) # placa/serie/motor
    otros_bienes = Column(Text, nullable=True)
    pais = Column(String(100), nullable=True)
    origen_bien = Column(String(100), nullable=True) # origen_del_bien

    # Relación back
    consulta = relationship("ConsultaMinuta", back_populates="bienes")
