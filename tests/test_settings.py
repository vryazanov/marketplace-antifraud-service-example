from src.settings import Settings


def test_provisioned_url_accepts_postgres_scheme(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_CONNECTION_STRING", "postgres://u:p@db:5432/test")
    settings = Settings(_env_file=None)
    assert settings.async_database_url() == "postgresql+asyncpg://u:p@db:5432/test"


def test_key_is_redacted_in_settings_repr():
    assert "private-value" not in repr(Settings(lms_llm_api_key="private-value"))
