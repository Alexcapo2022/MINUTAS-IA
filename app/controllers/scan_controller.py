from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.services.scan_service import ScanService

class ScanController:
    @staticmethod
    def scan_medio_pago(co_notaria: str, file: UploadFile, db: Session):
        # Delegamos toda la lógica de negocio al Service
        return ScanService.scan_medio_pago(co_notaria, file, db)
