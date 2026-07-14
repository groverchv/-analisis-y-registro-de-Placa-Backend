from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Lector de Placas UAGRM"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/alpr_db"

    # Detection configuration
    ROBOFLOW_API_KEY: str = ""
    ROBOFLOW_MODEL_ID: str = "license-plate-recognition-rxg4e/4"
    LOCAL_YOLO_MODEL_PATH: str = str(BASE_DIR / "ml" / "models" / "best.pt")
    DETECTION_CONFIDENCE_THRESHOLD: float = 0.35

    # Validation Rules
    CONFIDENCE_THRESHOLD: float = 0.70

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production"}:
                return False
        return bool(value)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
