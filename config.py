from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-6-luna"
    ai_timeout_seconds: float = 45.0
    cors_origins: str = "http://localhost:5173"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    mfa_issuer: str = "Planejador Financeiro 360"
    security_headers_enabled: bool = True
    environment: str = "development"
    require_strong_jwt_secret: bool = True
    agent_enabled: bool = True
    rate_limit_per_minute: int = 10
    privacy_policy_version: str = "1.0"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.environment.lower() == "production" and self.require_strong_jwt_secret:
            if len(self.jwt_secret) < 32 or self.jwt_secret in {"CHANGE_ME", "change-this-in-production"}:
                raise ValueError("JWT_SECRET forte é obrigatório em produção")
        return self

settings = Settings()
