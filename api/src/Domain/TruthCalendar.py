from datetime import datetime
from pydantic import BaseModel, ConfigDict

class TruthCalendar(BaseModel):
    id: int
    title: str
    start: datetime
    end: datetime
    updated_at: datetime

    model_config = ConfigDict(frozen=True)
