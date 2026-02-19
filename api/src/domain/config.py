from pydantic import BaseModel, HttpUrl
from typing import List
import yaml
from pathlib import Path

class Provider(BaseModel):
    url: HttpUrl
    name: str

class Config(BaseModel):
    external_providers: List[Provider]
    
    @classmethod
    def load(cls, path: str = "providers.yaml"):
        # Go up from src/ to project root
        config_path = Path(__file__).parent.parent.parent /"config" / path
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)