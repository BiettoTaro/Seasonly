from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Seasonly"
    app_env: str = "local"
    app_debug: bool = False

    database_url: str = Field(
        default="postgresql+asyncpg://seasonly:seasonly_dev_password@localhost:5432/seasonly"
    )

    auth_secret_key: str = "change-this-before-real-use"
    auth_access_token_expire_minutes: int = 30
    auth_refresh_token_expire_days: int = 30
    auth_password_reset_token_expire_minutes: int = 30


settings = Settings()
