from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.controllers.scan_controller import ScanController

router = APIRouter()

@router.post("")
def scan_medio_pago(
    token: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint para escanear medios de pago usando IA.
    Recibe la imagen y el token de seguridad para identificar la notaría.
    """
    return ScanController.scan_medio_pago(token=token, file=file, db=db)
