# main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException

from app.api.v1.router import router as v1_router

app = FastAPI(
    title="API Minutas",
    version="1.0.0",
    description="Extracción estructurada de minutas notariales usando GPT."
)

@app.get("/")
def root():
    return {"ok": True, "docs": "/docs", "health": "/health"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": "Solicitud inválida. Revisa los campos enviados.", "errors": exc.errors()},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if detail == "There was an error parsing the body":
        detail = "Hubo un error al procesar el cuerpo de la petición. Asegurate de enviar form-data (UploadFile) con los multipart correctos, no un JSON."
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
        headers=exc.headers
    )

# routers versionados
app.include_router(v1_router)
