from pydantic import BaseModel


class SyncStatusErrorResponse(BaseModel):
    provider: str
    error_code: str
    error_description: str