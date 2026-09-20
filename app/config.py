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

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
