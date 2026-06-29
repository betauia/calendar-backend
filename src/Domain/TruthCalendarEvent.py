from pydantic import BaseModel

from src.Domain.CalendarEventInfo import CalendarEventInfo
from src.Domain.CalendarEventMetaInfo import CalendarEventMetaInfo

class TruthCalendarEvent(BaseModel):
    id: int
    event_info: CalendarEventInfo
    event_meta_info: CalendarEventMetaInfo

    # Dont know what this does
    # model_config = ConfigDict(frozen=True)
