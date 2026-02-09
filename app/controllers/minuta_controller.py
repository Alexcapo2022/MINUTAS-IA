# app/controllers/minuta_controller.py
from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.services.minuta_service import MinutaService

async def extract_minuta(db: Session, file: UploadFile, co_cnl: str) -> dict:
    service = MinutaService(db)
    return await service.extract(file=file, co_cnl=co_cnl)
