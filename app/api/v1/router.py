# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.routes.minuta_routes import router as minuta_router

router = APIRouter()
router.include_router(minuta_router)
