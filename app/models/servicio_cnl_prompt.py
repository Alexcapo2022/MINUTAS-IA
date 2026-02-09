from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


class ServicioCnlPrompt(Base):
    __tablename__ = "r_servicio_cnl_prompt"

    co_cnl_prompt = Column(Integer, primary_key=True, autoincrement=True)

    co_servicio_cnl = Column(
        Integer,
        ForeignKey("p_servicio_cnl.co_servicio_cnl", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )

    co_prompt = Column(
        Integer,
        ForeignKey("p_prompt.co_prompt", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )

    fe_creacion = Column(DateTime, nullable=False)
    in_estado = Column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint("co_servicio_cnl", "co_prompt", name="uq_rsp_servicio_prompt"),
    )

    # Relaciones ORM
    servicio = relationship("ServicioCnl", back_populates="prompts_rel")
    prompt = relationship("Prompt", back_populates="servicios_rel")
