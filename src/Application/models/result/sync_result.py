from pydantic import BaseModel

from Application.models.result.calendar_sync_result import CalendarSyncResult


class SyncResult(BaseModel):
    calendar_sync_statuses: list[CalendarSyncResult]