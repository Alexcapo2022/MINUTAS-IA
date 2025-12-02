from fastapi import APIRouter, HTTPException, UploadFile, File
from app.controllers.poderes_controller import PoderResponse, parse_poder
from app.controllers.constituciones_controller import ConstitucionResponse, parse_constitucion
from app.controllers.compraventa_controller import CompraVentaResponse, parse_compra_venta  # 👈 nuevo

router = APIRouter(prefix="/api/minutas", tags=["Minutas"])

@router.post("/poder", response_model=PoderResponse)
async def parse_endpoint(file: UploadFile | None = File(
    default=None,
    description="Archivo PDF o Word (DOC/DOCX) en el campo form-data 'file'"
)):
    try:
        if file is None:
            raise HTTPException(
                status_code=400,
                detail="Debes adjuntar un archivo en el campo form-data 'file' (PDF o Word)."
            )
        result = await parse_poder(file)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/constituciones", response_model=ConstitucionResponse)
async def parse_constitucion_endpoint(
    file: UploadFile | None = File(default=None, description="Archivo PDF o Word (DOC/DOCX) en 'file'")
):
    try:
        if file is None:
            raise HTTPException(status_code=400, detail="Debes adjuntar un archivo en 'file' (PDF o Word).")
        return await parse_constitucion(file)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/compra-venta", response_model=CompraVentaResponse)
async def parse_compra_venta_endpoint(
    file: UploadFile | None = File(default=None, description="Archivo PDF o Word (DOC/DOCX) en 'file'")
):
    try:
        if file is None:
            raise HTTPException(status_code=400, detail="Debes adjuntar un archivo en 'file' (PDF o Word).")
        return await parse_compra_venta(file)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))