from fastapi import APIRouter, HTTPException, UploadFile, File
from app.controllers.poderes_controller import PoderResponse, parse_poder

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
