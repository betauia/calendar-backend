from pydantic import BaseModel, HttpUrl


class ExternalProvider(BaseModel, frozen=True):
    name: str
    url: HttpUrl