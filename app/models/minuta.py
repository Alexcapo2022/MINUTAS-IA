from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, Text, ForeignKey, Float, JSON, func
from sqlalchemy.dialects.mysql import LONGBLOB, LONGTEXT
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
    co_seguridad = Column(Integer, nullable=True)
    no_notaria = Column(String(255), nullable=True)
    minuta_legasys = Column(LONGBLOB, nullable=True) # Archivo DOCX Inteligente final
    fe_creacion = Column(DateTime, default=datetime.now)

    # Relaciones
    participantes = relationship("ParticipanteMinuta", back_populates="consulta", cascade="all, delete-orphan")
    valores = relationship("ValorMinutaMaster", back_populates="consulta", cascade="all, delete-orphan")
    bienes = relationship("BienMinuta", back_populates="consulta", cascade="all, delete-orphan")
    auditoria = relationship("MinutaAuditoria", back_populates="consulta", uselist=False, cascade="all, delete-orphan")

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
    ciiu = Column(String(255), nullable=True)
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
    rol = Column(String(255), nullable=True)
    relacion = Column(String(50), nullable=True)
    
    # Datos Financieros / Participación
    porcentaje_participacion = Column(Float, default=0.0)
    nu_acciones = Column(Integer, default=0)
    nu_acciones_suscritas = Column(Integer, default=0)
    mo_aportado = Column(Float, default=0.0)

    # Relación back
    consulta = relationship("ConsultaMinuta", back_populates="participantes")

class ValorMinutaMaster(Base):
    """
    Tabla Maestra para agrupar operaciones financieras (Transferencia + Medio Pago).
    """
    __tablename__ = "a_valor_minuta"

    id_valor = Column(Integer, primary_key=True, autoincrement=True)
    id_consulta = Column(Integer, ForeignKey("p_consulta_minuta.id_consulta"), nullable=False)
    tipo_registro = Column(String(20), default="VALOR")
    
    # Relaciones
    consulta = relationship("ConsultaMinuta", back_populates="valores")
    transferencia = relationship("ValorTransferencia", back_populates="master", uselist=False, cascade="all, delete-orphan")
    medio_pago = relationship("ValorMedioPago", back_populates="master", uselist=False, cascade="all, delete-orphan")

class ValorTransferencia(Base):
    """
    Detalle de la transferencia financiera.
    """
    __tablename__ = "a_valor_transferencia"

    id_transferencia = Column(Integer, primary_key=True, autoincrement=True)
    id_valor = Column(Integer, ForeignKey("a_valor_minuta.id_valor"), nullable=False)
    
    moneda = Column(String(10), nullable=True)
    co_moneda = Column(Integer, nullable=True)
    monto = Column(Numeric(18, 2), nullable=True)
    forma_pago = Column(String(100), nullable=True)
    oportunidad_pago = Column(String(100), nullable=True)

    master = relationship("ValorMinutaMaster", back_populates="transferencia")

class ValorMedioPago(Base):
    """
    Detalle del medio de pago utilizado.
    """
    __tablename__ = "a_valor_medio_pago"

    id_medio_pago = Column(Integer, primary_key=True, autoincrement=True)
    id_valor = Column(Integer, ForeignKey("a_valor_minuta.id_valor", ondelete="CASCADE"), nullable=False)
    
    medio_pago = Column(String(100))
    moneda = Column(String(10))
    co_moneda = Column(Integer)
    valor_bien = Column(Numeric(18, 2))
    fecha_pago = Column(Date)
    bancos = Column(String(100))
    documento_pago = Column(String(100))

    master = relationship("ValorMinutaMaster", back_populates="medio_pago")

class MinutaAuditoria(Base):
    """
    Tabla para auditoría profunda y telemetría de la extracción.
    Almacena el JSON crudo de la IA para debug y métricas de consumo.
    """
    __tablename__ = "a_minuta_auditoria"

    id_auditoria = Column(Integer, primary_key=True, autoincrement=True)
    id_consulta = Column(Integer, ForeignKey("p_consulta_minuta.id_consulta", ondelete="CASCADE"), nullable=False)
    
    raw_json = Column(LONGTEXT)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    model = Column(String(50))
    latency_ms = Column(Float)
    metadata_json = Column(JSON)  # Para datos extra
    fe_creacion = Column(DateTime, server_default=func.now())

    consulta = relationship("ConsultaMinuta", back_populates="auditoria")

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

class PSeguridad(Base):
    __tablename__ = "p_seguridad"

    co_seguridad = Column(Integer, primary_key=True, autoincrement=True)
    co_notaria = Column(Integer, nullable=True)
    name = Column(String(255), nullable=True)
    
    credenciales = relationship("HCredencialSeguridad", back_populates="seguridad")

class HCredencialSeguridad(Base):
    __tablename__ = "h_credencial_seguridad"

    co_credencial_seguridad = Column(Integer, primary_key=True, autoincrement=True)
    co_seguridad = Column(Integer, ForeignKey("p_seguridad.co_seguridad"), nullable=False)
    no_token_api = Column(Text, nullable=True)
    in_estado = Column(Integer, nullable=True)
    
    seguridad = relationship("PSeguridad", back_populates="credenciales")

