from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_ANON_KEY: str
    
    TELEGRAM_BOT_TOKEN: str = ""
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "alerts@cronwatch.dev"
    APP_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
