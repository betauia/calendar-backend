import json
from pathlib import Path
from src.domain.client import AppConfig, ClientConfig

def load_clients_from_config(config_filepath: str) -> AppConfig:
    raw = json.loads(Path(config_filepath).read_text())
    return AppConfig.model_validate(raw)

if __name__ == "__main__":
    load_clients_from_config("config/appsettings.json")