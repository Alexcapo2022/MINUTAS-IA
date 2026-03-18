from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base


class ServicioCnl(Base):
    __tablename__ = "p_servicio_cnl"

    co_servicio_cnl = Column(Integer, primary_key=True, autoincrement=True)
    co_cnl = Column(String(4), nullable=True)
    de_servicio = Column(String(250), nullable=True)
    in_estado = Column(Integer, nullable=True)
    fe_creacion = Column(DateTime, nullable=True)

    # ── Parametrización de participantes ──────────────────────────────────────
    # no_*   : label personalizado para ese rol en este servicio
    #          (p.ej. "VENDEDOR", "COMPRADOR"). Si es NULL se usa el genérico.
    # min_*  : mínimo de participantes que el LLM debe intentar identificar.
    #          0 = no aplica / no se inyecta esta regla en el prompt.
    # in_tipo_* : tipo de persona permitido.
    #          0 = NO APLICA  1 = SOLO NATURAL  2 = SOLO JURIDICA  3 = AMBAS

    no_otorgante = Column(String(255), nullable=True)
    min_otorgante = Column(Integer, nullable=False, default=0)
    in_tipo_otorgante = Column(Integer, nullable=False, default=0)

    no_beneficiario = Column(String(255), nullable=True)
    min_beneficiario = Column(Integer, nullable=False, default=0)
    in_tipo_beneficiario = Column(Integer, nullable=False, default=0)

    no_otro = Column(String(255), nullable=True)
    min_otro = Column(Integer, nullable=False, default=0)
    in_tipo_otro = Column(Integer, nullable=False, default=0)

    # ── Parametrización de valores ────────────────────────────────────────────
    # 0 = NO APLICA   1 = OBLIGATORIO   2 = OPCIONAL
    in_medio_pago = Column(Integer, nullable=False, default=0)
    in_oportunidad_pago = Column(Integer, nullable=False, default=0)

    # ── Parametrización de bienes ─────────────────────────────────────────────
    # in_bienes: 0 = NO APLICA, 1 = OBLIGATORIO, 2 = OPCIONAL
    in_bienes = Column(Integer, nullable=False, default=0)
    # in_aporte_bienes: 0 = NORMAL, 1 = APORTE DE CAPITAL (Activa regla matemática vs medioPago)
    in_aporte_bienes = Column(Integer, nullable=False, default=0)

    # ── Relaciones ────────────────────────────────────────────────────────────
    prompts_rel = relationship(
        "ServicioCnlPrompt",
        back_populates="servicio",
        cascade="all, delete-orphan",
    )
