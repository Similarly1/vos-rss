from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Vos API"
    database_url: str = "sqlite:///./vos.db"
    mistral_api_key: str = ""
    gemini_api_key: str = ""
    langsearch_api_key: str = ""
    synthesis_provider: str = "mistral"
    vectorization_provider: str = "mistral"
    synthesis_fallback_provider: str = "gemini"
    vectorization_fallback_provider: str = "gemini"
    mistral_model: str = "mistral-small-latest"
    gemini_model: str = "gemini-1.5-flash"
    mistral_article_model: str = "mistral-small-latest"
    gemini_article_model: str = "gemini-1.5-flash"
    mistral_discover_model: str = "mistral-small-latest"
    gemini_discover_model: str = "gemini-1.5-flash"
    mistral_podcast_model: str = "mistral-large-latest"
    gemini_podcast_model: str = "gemini-1.5-pro"
    mistral_embed_model: str = "mistral-embed"
    gemini_embed_model: str = "text-embedding-004"
    fallback_enabled: bool = True  # Retro-compatibility
    refresh_interval_minutes: int = 30
    article_retention_days: int = 14
    article_language: str = "fr"
    full_text_only: bool = False
    
    podcast_feed_token: str = ""
    cors_origins: list[str] = ["*"]
    base_url: str = "http://127.0.0.1:8000"  # Can be overridden in .env (ex: BASE_URL=https://my-vps-domain.com)
    secret_key: str = "YOUR_SUPER_SECRET_KEY_REPLACE_ME_IN_PRODUCTION!"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
