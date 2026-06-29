from pydantic import BaseModel

from src.Domain.ExternalProvider import ExternalProvider
from src.Domain.RemoteCalendarEvent import RemoteCalendarEvent


class RemoteCalendar(BaseModel):
    external_provider: ExternalProvider
    
    calendar_events: list[RemoteCalendarEvent] = []

    # model_config = ConfigDict(frozen=True)
