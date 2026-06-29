from datetime import datetime
from pydantic import BaseModel

class CalendarEventMetaInfo(BaseModel):
    created_at: datetime
    updated_at: datetime | None = None