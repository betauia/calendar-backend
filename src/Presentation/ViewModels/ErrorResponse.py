# src/Presentation/ViewModels/ErrorResponse.py
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error_code: str
    message: str