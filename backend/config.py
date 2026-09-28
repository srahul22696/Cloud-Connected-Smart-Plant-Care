from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./plantcare.db"
    app_secret: str = ""
    access_token_minutes: int = 60
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    device_offline_seconds: int = 180
    max_history_rows: int = 500
    allow_registration: bool = True
    max_pump_seconds: int = 10
    default_pump_seconds: int = 3
    watering_cooldown_seconds: int = 300
    app_env: str = "development"

settings = Settings()
