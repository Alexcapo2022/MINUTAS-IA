# app/schemas/minuta_schema.py
from pydantic import BaseModel

class MinutaExtractResponse(BaseModel):
    co_cnl: str
    payload: dict
