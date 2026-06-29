from pydantic import BaseModel

from src.Domain.TruthCalendarEvent import TruthCalendarEvent


class TruthCalendar(BaseModel):
    
    calendar_events: list[TruthCalendarEvent] = []
    

    # model_config = ConfigDict(frozen=True)
