from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # Database
    database_url: str

    # Security
    secret_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # Refresh cookie settings
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: str = "lax"

    # LLM
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    llm_provider: str = "groq"
    llm_model: str = "llama-3.3-70b-versatile"

    # Search
    tavily_api_key: str = ""

    # App
    debug: bool = False


settings = Settings()