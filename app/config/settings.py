from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Lector de Placas UAGRM"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Database (Global Neon Database)
    DATABASE_URL: str = "postgresql+psycopg://neondb_owner:npg_Z5WMe3ICfrFx@ep-misty-recipe-adlghyw1-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    
    # Roboflow API configuration
    ROBOFLOW_API_KEY: str = ""
    ROBOFLOW_MODEL_ID: str = "blpr-v4yyh/1"
    
    # Validation Rules
    CONFIDENCE_THRESHOLD: float = 0.70

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
