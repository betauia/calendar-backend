from pydantic import BaseModel, AnyUrl

class ClientConfig(BaseModel):
    name: str
    baseUrl: AnyUrl
    enabled: bool = True