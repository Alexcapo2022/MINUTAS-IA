# main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.routes.poderes_routes import router as poderes_router

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

# errores de validación más claros (400 en vez de 422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": "Solicitud inválida. Revisa los campos enviados.", "errors": exc.errors()},
    )

app.include_router(poderes_router)
