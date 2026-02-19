from datetime import datetime

from pydantic import BaseModel


class EventCreateDTO(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime