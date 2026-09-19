import pytest
from pydantic import ValidationError

from lib.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DB_USER", "pictohistorias")
    monkeypatch.setenv("DB_PASSWORD", "secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    monkeypatch.delenv("DB_HOST", raising=False)

    settings = Settings(_env_file=None)

    assert settings.db_user == "pictohistorias"
    assert settings.db_password == "secret"
    assert settings.openai_api_key == "sk-fake"
    assert settings.db_host == "localhost"
    assert settings.qdrant_collection == "arasaac_es"
    assert settings.logcentral_log_dir == "logs"
    assert settings.anthropic_api_key is None


def test_settings_loads_anthropic_api_key_when_set(monkeypatch):
    monkeypatch.setenv("DB_USER", "pictohistorias")
    monkeypatch.setenv("DB_PASSWORD", "secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")

    settings = Settings(_env_file=None)

    assert settings.anthropic_api_key == "sk-ant-fake"


def test_settings_requires_db_user(monkeypatch):
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.setenv("DB_PASSWORD", "secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
