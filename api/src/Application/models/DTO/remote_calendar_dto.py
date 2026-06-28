from pydantic import BaseModel

from Application.models.DTO.remote_calendar_event_dto import RemoteCalendarEventDTO

class RemoteCalendarDTO(BaseModel):
    events: list[RemoteCalendarEventDTO]