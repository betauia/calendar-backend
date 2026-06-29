from pydantic import BaseModel

from Presentation.ViewModels.SyncStatusCounts import SyncStatusCounts


class SyncStatusResponse(BaseModel):
    provider: str
    counts: SyncStatusCounts