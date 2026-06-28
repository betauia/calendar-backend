from datetime import datetime
from pydantic import BaseModel

class CalendarEventInfo(BaseModel):
    title: str
    description: str | None = None
    location: str | None = None
    starts_at: datetime
    ends_at: datetime
    # created_at: datetime
    # updated_at: datetime | None = None
    # Moved to separate class CalendarEventMetaInfo