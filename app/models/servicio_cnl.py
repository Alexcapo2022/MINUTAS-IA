from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base


class ServicioCnl(Base):
    __tablename__ = "p_servicio_cnl"

    co_servicio_cnl = Column(Integer, primary_key=True, autoincrement=True)
    co_cnl = Column(String(4), nullable=True)          # char(4) en MySQL
    de_servicio = Column(String(250), nullable=True)
    in_estado = Column(Integer, nullable=True)
    fe_creacion = Column(DateTime, nullable=True)

    # Relación a tabla puente
    prompts_rel = relationship(
        "ServicioCnlPrompt",
        back_populates="servicio",
        cascade="all, delete-orphan",
    )
