from pydantic import BaseModel, model_validator

from src.Domain.RemoteCalendarEvent import RemoteCalendarEvent
from src.Domain.TruthCalendarEvent import TruthCalendarEvent
from src.Domain.SyncStatus import SyncStatus


class EventSyncResult(BaseModel):
    truth_event: TruthCalendarEvent | None = None
    remote_event: RemoteCalendarEvent | None = None
    sync_status: SyncStatus
    
    @model_validator(mode="after")
    def validate_consistency(self) -> "EventSyncResult":
        if self.sync_status == SyncStatus.AHEAD:
            if self.truth_event is not None:
                raise ValueError("AHEAD status must not have a truth_event")
            if self.remote_event is None:
                raise ValueError("AHEAD status requires a remote_event")

        elif self.sync_status == SyncStatus.BEHIND:
            if self.truth_event is None:
                raise ValueError("BEHIND status requires a truth_event")

        elif self.sync_status == SyncStatus.SYNCED:
            if self.truth_event is None:
                raise ValueError("SYNCED status requires a truth_event")
            if self.remote_event is None:
                raise ValueError("SYNCED status requires a remote_event")

        return self