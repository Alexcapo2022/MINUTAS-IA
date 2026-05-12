from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.services.scan_service import ScanService

class ScanController:
    @staticmethod
    async def scan_medio_pago(token: str, file: UploadFile, referencia: str, db: Session):
        return await ScanService.scan_medio_pago(token=token, file=file, referencia=referencia, db=db)

    @staticmethod
    def get_historial(limit: int, offset: int, db: Session):
        return ScanService.get_historial(limit=limit, offset=offset, db=db)

    @staticmethod
    def get_image(filename: str, token: str, db: Session):
        from fastapi.responses import FileResponse
        file_path = ScanService.get_image(filename=filename, token=token, db=db)
        return FileResponse(file_path)
