# api/protocol/events.py
from pydantic import BaseModel
from typing import Literal


class IGenericEventDTO(BaseModel):
    provider: str
    name: str
    description: str | None
    start_time: str
    end_time: str | None
