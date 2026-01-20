from pydantic import BaseModel
from config.integrations import IntegrationConfig


class AppConfig(BaseModel):
    integrations: list[IntegrationConfig]
