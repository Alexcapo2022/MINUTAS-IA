from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.services.scan_service import ScanService

class ScanController:
    @staticmethod
    async def scan_medio_pago(token: str, file: UploadFile, referencia: str, db: Session):
        return await ScanService.scan_medio_pago(token=token, file=file, referencia=referencia, db=db)

    @staticmethod
    def get_historial(limit: int, offset: int, notaria: str, referencia: str, medio_pago: str, banco: str, fecha_desde: str, fecha_hasta: str, db: Session):
        return ScanService.get_historial(
            limit=limit, 
            offset=offset, 
            notaria=notaria,
            referencia=referencia,
            medio_pago=medio_pago,
            banco=banco,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            db=db
        )

    @staticmethod
    def get_image(filename: str, token: str, db: Session):
        from fastapi.responses import FileResponse
        file_path = ScanService.get_image(filename=filename, token=token, db=db)
        return FileResponse(file_path)
