from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class Prompt(Base):
    __tablename__ = "p_prompt"

    co_prompt = Column(Integer, primary_key=True, autoincrement=True)
    de_promp = Column(Text, nullable=True)  # longtext
    de_alias_prompt = Column(String(250), nullable=True)
    fe_creacion = Column(DateTime, nullable=True)
    fe_modificacion = Column(DateTime, nullable=True)
    in_estado = Column(Integer, nullable=True)

    # Relación a tabla puente
    servicios_rel = relationship(
        "ServicioCnlPrompt",
        back_populates="prompt",
        cascade="all, delete-orphan",
    )
