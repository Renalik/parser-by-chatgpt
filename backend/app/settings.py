from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    dgis_api_key: str = ""
    database_url: str = "sqlite:///./data/parser.db"
    app_password: str = ""
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    retention_days: int = 7
    desktop_mode: bool = False
    desktop_data_dir: str = ""


settings = Settings()
Path("data").mkdir(exist_ok=True)
