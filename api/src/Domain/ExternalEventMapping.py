from pydantic import BaseModel

from Domain.ExternalProvider import ExternalProvider
from Domain.SyncStatus import SyncStatus

class ExternalEventMapping(BaseModel):
    truth_event_id: int
    external_id: str
    provider: ExternalProvider
    status: SyncStatus