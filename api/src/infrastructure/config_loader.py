import yaml
from pathlib import Path
from pydantic import BaseModel, HttpUrl
from typing import List

class Provider(BaseModel):
    name: str
    url: HttpUrl

class Config(BaseModel):
    external_providers: List[Provider]

    @classmethod
    def load(cls, path: str = "providers.yaml"):
        config_path = Path(__file__).parent.parent.parent / "config" / path
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
