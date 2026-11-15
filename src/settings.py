from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", populate_by_name=True
    )
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5436/antifraud_db",
        validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_CONNECTION_STRING"),
    )
    lms_llm_api_key: SecretStr = SecretStr("")
    jev_base_url: str = "https://llm.python-labs.ru/v1/"
    jev_timeout_seconds: float = Field(default=120, gt=0, le=300)
    antifraud_threshold: float = Field(default=0.85, gt=0, le=1)

    def async_database_url(self) -> str:
        for scheme in ("postgres://", "postgresql://"):
            if self.database_url.startswith(scheme):
                return "postgresql+asyncpg://" + self.database_url[len(scheme) :]
        return self.database_url
