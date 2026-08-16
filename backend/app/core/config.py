from typing import ClassVar

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.data.enums import RecommendationRankingStrategy


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Seasonly"
    app_env: str = "local"
    app_debug: bool = False
    app_force_https: bool = False
    app_trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    trust_proxy_location_headers: bool = False

    database_url: str = Field(
        default="postgresql+asyncpg://seasonly:seasonly_dev_password@localhost:5432/seasonly"
    )

    auth_secret_key: str = "change-this-before-real-use"
    auth_access_token_expire_minutes: int = 30
    auth_refresh_token_expire_days: int = 30
    auth_password_reset_token_expire_minutes: int = 30
    auth_rate_limit_requests: int = 10
    auth_rate_limit_window_seconds: int = 60

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_starttls: bool = True
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from_email: str | None = None

    recipes_api_key: str | None = None
    recipes_base_url: str = "https://www.themealdb.com/api/json/v2/"
    recipes_request_timeout_seconds: float = 20.0
    recipes_request_retries: int = 2

    recommendation_ranking_mode: RecommendationRankingStrategy = (
        RecommendationRankingStrategy.SEASONAL_TFIDF_V1
    )

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        environment = self.app_env.strip().lower()
        self.app_env = environment
        if self.auth_rate_limit_requests < 1:
            raise ValueError("AUTH_RATE_LIMIT_REQUESTS must be positive")
        if self.auth_rate_limit_window_seconds < 1:
            raise ValueError("AUTH_RATE_LIMIT_WINDOW_SECONDS must be positive")
        if self.auth_access_token_expire_minutes < 1:
            raise ValueError("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
        if self.auth_refresh_token_expire_days < 1:
            raise ValueError("AUTH_REFRESH_TOKEN_EXPIRE_DAYS must be positive")
        if self.auth_password_reset_token_expire_minutes < 1:
            raise ValueError("AUTH_PASSWORD_RESET_TOKEN_EXPIRE_MINUTES must be positive")
        if environment in {"production", "prod"}:
            if self.app_debug:
                raise ValueError("APP_DEBUG must be false in production")
            if not self.app_force_https:
                raise ValueError("APP_FORCE_HTTPS must be true in production")
            if (
                len(self.auth_secret_key) < 32
                or self.auth_secret_key == "change-this-before-real-use"
            ):
                raise ValueError("AUTH_SECRET_KEY must be a unique value of at least 32 characters")
            local_hosts = {"localhost", "127.0.0.1", "testserver"}
            if (
                not self.app_trusted_hosts
                or "*" in self.app_trusted_hosts
                or set(self.app_trusted_hosts) <= local_hosts
            ):
                raise ValueError("APP_TRUSTED_HOSTS must contain explicit production hostnames")
            if "seasonly_dev_password" in self.database_url:
                raise ValueError("DATABASE_URL must not use the development password in production")
            if not self.recipes_base_url.startswith("https://"):
                raise ValueError("RECIPES_BASE_URL must use HTTPS in production")
            if not self.smtp_host or not self.smtp_from_email:
                raise ValueError("SMTP_HOST and SMTP_FROM_EMAIL are required in production")
        return self


settings = Settings()
