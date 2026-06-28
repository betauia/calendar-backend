from pydantic import BaseModel

from Application.models.result.event_sync_result import EventSyncResult
from Domain.RemoteCalendar import RemoteCalendar


class CalendarSyncResult(BaseModel):
    remote_calendar: RemoteCalendar
    event_statuses: list[EventSyncResult]