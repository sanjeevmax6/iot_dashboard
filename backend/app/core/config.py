# To unify all .env imports
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    # Adding this with /// to adapt to current dir.
    # TODO: enhancements to make runtime variable for deployment with AWS
    database_url: str = "sqlite+aiosqlite:///./iot_dashboard.db"

    # API
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    log_level: str = "INFO"

    # LLM
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    bedrock_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-haiku-4-5-20251001-v1:0"

    # AI Workflow
    max_ai_retries: int = 3
    analysis_rate_limit_seconds: int = 30
    top_at_risk_count: int = 3


settings = Settings()
