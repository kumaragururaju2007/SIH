from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base backend directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./storage/aicte.db"
    UPLOAD_DIR: str = "./storage/uploads"
    CONFIG_DIR: str = "./configs"

    # Extractor settings: rules | llm_api | llm_local
    EXTRACTOR: str = "rules"
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    CONFIDENCE_THRESHOLD: float = 0.70
    TESSERACT_CMD: Optional[str] = None
    RESET_DB_ON_STARTUP: bool = False
    REGISTRY_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Ensure directories exist
if settings.DATABASE_URL.startswith("sqlite:///"):
    sqlite_file = settings.DATABASE_URL.replace("sqlite:///", "")
    if sqlite_file != ":memory:":
        db_path = Path(sqlite_file)
        if not db_path.is_absolute():
            db_path = BASE_DIR / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.CONFIG_DIR).mkdir(parents=True, exist_ok=True)
