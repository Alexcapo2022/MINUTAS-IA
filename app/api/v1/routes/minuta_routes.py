# app/api/v1/routes/minuta_routes.py
from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.controllers.minuta_controller import extract_minuta
from app.schemas.minuta_schema import MinutaExtractResponse

router = APIRouter(prefix="/api/v1/minutas", tags=["Minutas"])

@router.post("/", response_model=MinutaExtractResponse)
async def extract_endpoint(
    co_cnl: str = Form(...),              # ejemplo: "0101"
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    payload = await extract_minuta(db=db, file=file, co_cnl=co_cnl)
    return payload
    
