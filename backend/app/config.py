from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Vos API"
    database_url: str = "sqlite:///./vos.db"
    mistral_api_key: str = ""
    cors_origins: list[str] = ["*"]
    base_url: str = "http://127.0.0.1:8000"  # Can be overridden in .env (ex: BASE_URL=https://my-vps-domain.com)

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
