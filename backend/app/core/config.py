from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    app_name: str = "Multi-Client Financial Report Automation Platform"
    database_url: str = f"sqlite:///{BASE_DIR / 'storage' / 'app.db'}"
    storage_root: Path = BASE_DIR / "storage"
    secret_key: str = "dev-secret-key-change-in-production-CHANGE-ME"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12
    soffice_binary: str = "soffice"
    validation_tolerance: float = 0.01

    model_config = SettingsConfigDict(env_prefix="FRA_")


settings = Settings()
settings.storage_root.mkdir(parents=True, exist_ok=True)
(settings.storage_root / "clients").mkdir(parents=True, exist_ok=True)
