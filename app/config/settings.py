from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Lector de Placas UAGRM"
    DEBUG: bool = False
    
    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/alpr_db"
    
    # Roboflow API configuration
    ROBOFLOW_API_KEY: str = ""
    ROBOFLOW_MODEL_ID: str = "blpr-v4yyh/1"
    
    # Validation Rules
    CONFIDENCE_THRESHOLD: float = 0.70

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
