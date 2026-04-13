# app/api/v1/routes/minuta_routes.py
from fastapi import APIRouter, UploadFile, File, Form, Depends, BackgroundTasks
from sqlalchemy.orm import Session
import httpx
import logging

logger = logging.getLogger(__name__)

from app.db.session import get_db
from app.controllers.minuta_controller import extract_minuta
from app.schemas.minuta_schema import MinutaExtractResponse

router = APIRouter(prefix="/api/v1/minutas", tags=["Minutas"])

async def notify_orchestrator(id_consulta: int):
    url = f"http://161.132.68.187:8003/api/orchestrator/start/{id_consulta}"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, timeout=5.0)
            logger.info(f"Orquestador notificado con id_consulta={id_consulta}")
    except Exception as e:
        logger.error(f"Error al notificar al Orquestador: {e}")

@router.post("", response_model=MinutaExtractResponse)
@router.post("/", response_model=MinutaExtractResponse)
async def extract_endpoint(
    background_tasks: BackgroundTasks,
    co_cnl: str = Form(...),              # ejemplo: "0101"
    token: str = Form(None),              # Token de seguridad para el API
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    payload = await extract_minuta(db=db, file=file, co_cnl=co_cnl, token=token)
    
    # Extraemos id_consulta para avisarle al orquestador en background
    if isinstance(payload, dict):
        try:
            id_con = payload.get("payload", {}).get("id_consulta")
            if id_con:
                background_tasks.add_task(notify_orchestrator, id_con)
        except Exception:
            pass

    return payload
    
