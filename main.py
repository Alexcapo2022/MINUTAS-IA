# main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

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

# routers versionados
app.include_router(v1_router)
