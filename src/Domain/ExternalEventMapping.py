from pydantic import BaseModel

from src.Domain.ExternalProvider import ExternalProvider
from src.Domain.SyncStatus import SyncStatus

class ExternalEventMapping(BaseModel):
    truth_event_id: int
    external_id: str
    provider: ExternalProvider
    status: SyncStatus