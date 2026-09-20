from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 60
    first_admin_email: str
    first_admin_password: str
    # comma-separated in .env (e.g. "http://localhost:5173,http://localhost:3000") rather than a
    # list field, since pydantic-settings otherwise expects list-typed env vars to be JSON.
    cors_origins: str = "http://localhost:5173"

    # "log" (default) just logs would-be emails - safe for local dev/tests, never touches a real
    # mail server. Switch to "smtp" (and fill in the smtp_* fields) to actually send mail.
    email_backend: Literal["log", "smtp"] = "log"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_from_email: str = "noreply@stockflow.local"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
