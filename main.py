from fastapi import FastAPI
from app.routes.poderes_routes import router as poderes_router

app = FastAPI(
    title="API Minutas",
    version="1.0.0",
    description="Extracción estructurada de minutas notariales usando GPT."
)

app.include_router(poderes_router)

@app.get("/health")
def health():
    return {"status": "ok"}