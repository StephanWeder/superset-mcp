from __future__ import annotations

import asyncio

import httpx

from superset_mcp.client import SupersetClient
from superset_mcp.config import SupersetSettings


def _build_client(handler: httpx.MockTransport) -> SupersetClient:
    settings = SupersetSettings(
        base_url="https://superset.example.com",
        username="admin",
        password="secret",
    )
    client = SupersetClient(settings)
    client._client = httpx.AsyncClient(
        base_url=settings.base_url,
        timeout=45.0,
        verify=settings.verify_ssl,
        transport=handler,
    )
    return client


def test_write_requests_include_csrf_token() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)

        if request.url.path == "/api/v1/security/login":
            return httpx.Response(200, json={"access_token": "access-token"})
        if request.url.path == "/api/v1/security/csrf_token/":
            assert request.headers["Authorization"] == "Bearer access-token"
            return httpx.Response(200, json={"result": "csrf-token"})
        if request.url.path == "/api/v1/chart/":
            assert request.headers["Authorization"] == "Bearer access-token"
            assert request.headers["X-CSRFToken"] == "csrf-token"
            assert request.headers["Referer"] == "https://superset.example.com"
            return httpx.Response(201, json={"id": 10})

        return httpx.Response(404, json={"message": "not found"})

    client = _build_client(httpx.MockTransport(handler))
    result = asyncio.run(client.create_resource("chart", {"slice_name": "demo"}))

    assert result["id"] == 10
    assert [req.url.path for req in calls] == [
        "/api/v1/security/login",
        "/api/v1/security/csrf_token/",
        "/api/v1/chart/",
    ]

    asyncio.run(client.close())


def test_csrf_token_is_cached_for_subsequent_writes() -> None:
    csrf_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal csrf_calls

        if request.url.path == "/api/v1/security/login":
            return httpx.Response(200, json={"access_token": "access-token"})
        if request.url.path == "/api/v1/security/csrf_token/":
            csrf_calls += 1
            return httpx.Response(200, json={"result": "csrf-token"})
        if request.url.path == "/api/v1/chart/":
            return httpx.Response(201, json={"id": 10})

        return httpx.Response(404, json={"message": "not found"})

    client = _build_client(httpx.MockTransport(handler))

    asyncio.run(client.create_resource("chart", {"slice_name": "first"}))
    asyncio.run(client.create_resource("chart", {"slice_name": "second"}))

    assert csrf_calls == 1
    asyncio.run(client.close())
