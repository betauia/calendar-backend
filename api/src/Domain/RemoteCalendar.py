from pydantic import BaseModel

from Domain.ExternalProvider import ExternalProvider
from Domain.RemoteCalendarEvent import RemoteCalendarEvent


class RemoteCalendar(BaseModel):
    external_provider: ExternalProvider
    
    calendar_events: list[RemoteCalendarEvent] = []

    # model_config = ConfigDict(frozen=True)
