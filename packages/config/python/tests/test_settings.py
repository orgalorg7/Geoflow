import pytest

from geoflow_config import Settings


def test_settings_have_safe_local_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.redis_url.endswith("/0")
    assert settings.celery_broker_url.endswith("/1")
    assert settings.celery_result_backend.endswith("/2")
