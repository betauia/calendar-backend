from pydantic import BaseModel

from Domain.CalendarEventInfo import CalendarEventInfo
from Domain.CalendarEventMetaInfo import CalendarEventMetaInfo

class TruthCalendarEvent(BaseModel):
    id: int
    event_info: CalendarEventInfo
    event_meta_info: CalendarEventMetaInfo

    # Dont know what this does
    # model_config = ConfigDict(frozen=True)
