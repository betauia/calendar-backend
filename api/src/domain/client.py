from pydantic import BaseModel, AnyUrl

class ClientConfig(BaseModel):
    name: str
    baseUrl: AnyUrl
    enabled: bool = True
    
    class Config:
        extra = "forbid"
    
class AppConfig(BaseModel):
    integrations: list[ClientConfig]
    
    class Config:
        extra = "forbid"