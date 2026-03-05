from __future__ import annotations

import os

import pytest

from superset_mcp.config import SupersetSettings


@pytest.fixture(autouse=True)
def clear_env() -> None:
    for key in [
        "SUPERSET_BASE_URL",
        "SUPERSET_USERNAME",
        "SUPERSET_PASSWORD",
        "SUPERSET_AUTH_PROVIDER",
        "SUPERSET_TOKEN_REFRESH_SECONDS",
        "SUPERSET_VERIFY_SSL",
    ]:
        os.environ.pop(key, None)


def test_settings_from_env_success() -> None:
    os.environ["SUPERSET_BASE_URL"] = "https://superset.example.com/"
    os.environ["SUPERSET_USERNAME"] = "admin"
    os.environ["SUPERSET_PASSWORD"] = "secret"
    os.environ["SUPERSET_VERIFY_SSL"] = "false"

    settings = SupersetSettings.from_env()

    assert settings.base_url == "https://superset.example.com"
    assert settings.username == "admin"
    assert settings.verify_ssl is False


def test_settings_missing_required_values() -> None:
    with pytest.raises(ValueError, match="SUPERSET_BASE_URL"):
        SupersetSettings.from_env()
