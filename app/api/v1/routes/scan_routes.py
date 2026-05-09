from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.controllers.scan_controller import ScanController

router = APIRouter()

@router.post("")
def scan_medio_pago(
    co_notaria: str = Form(...),
    token: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint para escanear medios de pago usando IA.
    Recibe la imagen, la notaría y el token de seguridad.
    """
    # TODO: Aquí se puede meter la lógica para descifrar el token 
    # y validar a qué notaría pertenece realmente.
    
    return ScanController.scan_medio_pago(co_notaria, file, db)
