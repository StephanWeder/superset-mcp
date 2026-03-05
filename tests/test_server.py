from __future__ import annotations

import asyncio
import importlib
import os

import pytest


@pytest.fixture
def server_module():
    os.environ["SUPERSET_BASE_URL"] = "https://superset.example.com"
    os.environ["SUPERSET_USERNAME"] = "admin"
    os.environ["SUPERSET_PASSWORD"] = "secret"
    mod = importlib.import_module("superset_mcp.server")
    return mod


def test_superset_raw_api_rejects_invalid_path(server_module) -> None:
    with pytest.raises(server_module.SupersetApiError):
        asyncio.run(server_module.superset_raw_api("GET", "/not-api", None, None))
