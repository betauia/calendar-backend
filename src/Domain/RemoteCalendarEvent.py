from pydantic import BaseModel

from Domain.CalendarEventInfo import CalendarEventInfo

class RemoteCalendarEvent(BaseModel):
    external_id: str
    event_info: CalendarEventInfo

    # Dont know what this does
    # model_config = ConfigDict(frozen=True)
