from __future__ import annotations

import os
from pathlib import Path

import pytest

from superset_mcp.config import SupersetSettings


@pytest.fixture(autouse=True)
def clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "SUPERSET_BASE_URL",
        "SUPERSET_USERNAME",
        "SUPERSET_PASSWORD",
        "SUPERSET_AUTH_PROVIDER",
        "SUPERSET_TOKEN_REFRESH_SECONDS",
        "SUPERSET_VERIFY_SSL",
        "SUPERSET_ENV_FILE",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_settings_from_env_success() -> None:
    os.environ["SUPERSET_BASE_URL"] = "https://superset.example.com/"
    os.environ["SUPERSET_USERNAME"] = "admin"
    os.environ["SUPERSET_PASSWORD"] = "secret"
    os.environ["SUPERSET_VERIFY_SSL"] = "false"

    settings = SupersetSettings.from_env()

    assert settings.base_url == "https://superset.example.com"
    assert settings.username == "admin"
    assert settings.verify_ssl is False


def test_settings_from_explicit_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / "superset.env"
    env_file.write_text(
        "\n".join(
            [
                "SUPERSET_BASE_URL=https://superset.internal",
                "SUPERSET_USERNAME=svc_user",
                "SUPERSET_PASSWORD=svc_password",
                "SUPERSET_VERIFY_SSL=false",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SUPERSET_ENV_FILE", str(env_file))

    settings = SupersetSettings.from_env()

    assert settings.base_url == "https://superset.internal"
    assert settings.username == "svc_user"
    assert settings.password == "svc_password"
    assert settings.verify_ssl is False


def test_settings_missing_required_values() -> None:
    with pytest.raises(ValueError, match="SUPERSET_BASE_URL"):
        SupersetSettings.from_env()
