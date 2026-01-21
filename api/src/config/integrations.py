# config/integrations.py
from pydantic import BaseModel, Field
from typing import Literal, Union


class BaseIntegrationConfig(BaseModel):
    enabled: bool = True
    type: Literal["discord"]
    base_api_url: str = Field(
        default="http://localhost:8000",
        description="Base URL of the external adapter API",
    )
