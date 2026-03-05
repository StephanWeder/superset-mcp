from __future__ import annotations

import asyncio

import pytest

from superset_mcp.client import SupersetApiError, SupersetClient
from superset_mcp.config import SupersetSettings


@pytest.fixture
def client() -> SupersetClient:
    settings = SupersetSettings(
        base_url="https://superset.example.com",
        username="admin",
        password="secret",
    )
    c = SupersetClient(settings)
    c._openapi_cache = {
        "paths": {
            "/api/v1/dashboard/{pk}": {
                "get": {
                    "operationId": "get_dashboard",
                    "summary": "Get dashboard",
                    "parameters": [{"name": "pk", "in": "path"}],
                    "tags": ["Dashboard"],
                }
            }
        }
    }
    return c


def test_list_operations_filters_by_tag(client: SupersetClient) -> None:
    result = asyncio.run(client.list_operations(tag="dashboard"))
    assert result["count"] == 1
    assert result["operations"][0]["operation_id"] == "get_dashboard"


def test_call_operation_missing_path_param_raises(client: SupersetClient) -> None:
    with pytest.raises(SupersetApiError, match="Missing required path parameter 'pk'"):
        asyncio.run(client.call_operation("get_dashboard"))
