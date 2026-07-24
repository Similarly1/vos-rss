from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Vos API"
    database_url: str = "sqlite:///./vos.db"
    mistral_api_key: str = ""
    gemini_api_key: str = ""
    synthesis_provider: str = "mistral"
    vectorization_provider: str = "mistral"
    mistral_model: str = "mistral-small-latest"
    gemini_model: str = "gemini-1.5-flash"
    fallback_enabled: bool = True
    refresh_interval_minutes: int = 30
    article_retention_days: int = 14
    article_language: str = "fr"
    full_text_only: bool = False
    
    podcast_feed_token: str = ""
    cors_origins: list[str] = ["*"]
    base_url: str = "http://127.0.0.1:8000"  # Can be overridden in .env (ex: BASE_URL=https://my-vps-domain.com)

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
