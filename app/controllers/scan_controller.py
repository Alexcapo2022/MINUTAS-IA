from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.services.scan_service import ScanService

class ScanController:
    @staticmethod
    async def scan_medio_pago(token: str, file: UploadFile, db: Session):
        return await ScanService.scan_medio_pago(token=token, file=file, db=db)
