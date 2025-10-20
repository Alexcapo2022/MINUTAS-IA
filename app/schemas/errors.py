from pydantic import BaseModel

class ErrorItem(BaseModel):
    code: str
    message: str

class WarningItem(BaseModel):
    code: str
    message: str
