from fastapi import FastAPI
from app.routers.extract import router as extract_router # type: ignore
from app.core.middleware import add_common_middleware # type: ignore

app = FastAPI(
    title="MVP Minutas (Refactor)",
    version="2.0.0",
)

# Middlewares (CORS, request timing, etc.)
add_common_middleware(app)

# Routers
app.include_router(extract_router)

# Root simple (compat)
@app.get("/")
def root():
    return {"message": "API viva. Usa /docs para probar /extract (view=compact|full)."}
