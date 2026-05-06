from pydantic import BaseModel, HttpUrl


class ExternalProvider(BaseModel):
    name: str
    url: HttpUrl