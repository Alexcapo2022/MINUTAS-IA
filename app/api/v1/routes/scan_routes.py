from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.controllers.scan_controller import ScanController

router = APIRouter(prefix="/api/v1/scan", tags=["Scan"])

@router.post("")
async def scan_medio_pago(
    token: str = Form(...),
    file: UploadFile = File(...),
    referencia: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Endpoint para escanear medios de pago usando IA.
    Recibe la imagen y el token de seguridad para identificar la notaría.
    """
    return await ScanController.scan_medio_pago(token=token, file=file, referencia=referencia, db=db)

@router.get("/historial")
def get_historial(
    limit: int = Query(10, ge=1, le=100, description="Cantidad de registros por página"),
    offset: int = Query(0, ge=0, description="Cantidad de registros a saltar"),
    referencia: str = Query(None, description="Filtro parcial por referencia"),
    medio_pago: str = Query(None, description="Filtro exacto por medio de pago"),
    banco: str = Query(None, description="Filtro exacto por banco"),
    fecha_desde: str = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_hasta: str = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de TODOS los escaneos paginado con filtros dinámicos (Solo para Administrador).
    """
    return ScanController.get_historial(
        limit=limit, 
        offset=offset, 
        referencia=referencia,
        medio_pago=medio_pago,
        banco=banco,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        db=db
    )

@router.get("/image/{filename}")
def get_image(
    filename: str,
    token: str = Query(..., description="Token de seguridad de la notaría dueña de la imagen"),
    db: Session = Depends(get_db)
):
    """
    Despacha la imagen física si y solo si el token provisto pertenece a la notaría
    que subió la imagen. Protege contra accesos no autorizados.
    """
    return ScanController.get_image(filename=filename, token=token, db=db)

