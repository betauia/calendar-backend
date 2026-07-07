from Domain.ProvidersConfig import ProvidersConfig
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppConfig(BaseSettings):
    database_url: str
    log_level: str = "INFO"
    providers: ProvidersConfig

    model_config = SettingsConfigDict(env_file=".env")