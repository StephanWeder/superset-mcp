"""Async Superset API client used by MCP tools."""

from __future__ import annotations

import time
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from superset_mcp.config import SupersetSettings


class SupersetApiError(RuntimeError):
    """Raised when Superset API call fails."""


class SupersetClient:
    """Thin async wrapper around Superset REST APIs with token refresh."""

    def __init__(self, settings: SupersetSettings) -> None:
        self._settings = settings
        self._access_token: str | None = None
        self._token_deadline: float = 0
        self._openapi_cache: dict[str, Any] | None = None
        self._client = httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=45.0,
            verify=settings.verify_ssl,
        )

    async def close(self) -> None:
        await self._client.aclose()

    @retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3), reraise=True)
    async def _login(self) -> None:
        response = await self._client.post(
            "/api/v1/security/login",
            json={
                "username": self._settings.username,
                "password": self._settings.password,
                "provider": self._settings.provider,
                "refresh": True,
            },
        )
        if response.status_code >= 400:
            raise SupersetApiError(
                f"Failed login ({response.status_code}): {response.text[:500]}"
            )

        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise SupersetApiError("Login succeeded but no access_token returned")

        self._access_token = token
        self._token_deadline = time.time() + self._settings.refresh_seconds

    async def _auth_headers(self) -> dict[str, str]:
        if not self._access_token or time.time() >= self._token_deadline:
            await self._login()
        return {"Authorization": f"Bearer {self._access_token}"}

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = await self._auth_headers()
        response = await self._client.request(
            method,
            path,
            headers=headers,
            params=params,
            json=json_body,
        )

        if response.status_code == 401:
            await self._login()
            headers = await self._auth_headers()
            response = await self._client.request(
                method,
                path,
                headers=headers,
                params=params,
                json=json_body,
            )

        if response.status_code >= 400:
            raise SupersetApiError(
                f"{method} {path} failed ({response.status_code}): {response.text[:1000]}"
            )

        if not response.content:
            return {"status": response.status_code}

        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            payload: dict[str, Any] = response.json()
            return payload

        return {
            "status": response.status_code,
            "raw_text": response.text,
        }

    async def get_openapi_spec(self, force_refresh: bool = False) -> dict[str, Any]:
        """Load and cache the Superset OpenAPI spec used for endpoint discovery."""
        if self._openapi_cache and not force_refresh:
            return self._openapi_cache

        for candidate in ("/swagger/v1", "/api/v1/_openapi"):
            try:
                spec = await self.request("GET", candidate)
            except SupersetApiError:
                continue
            if spec.get("paths"):
                self._openapi_cache = spec
                return spec

        raise SupersetApiError("Unable to load Superset OpenAPI spec from /swagger/v1 or /api/v1/_openapi")

    async def list_operations(
        self,
        *,
        tag: str | None = None,
        search: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """List API operations from OpenAPI for tool-friendly endpoint discovery."""
        spec = await self.get_openapi_spec(force_refresh=force_refresh)
        found: list[dict[str, Any]] = []

        query = search.lower().strip() if search else None
        tag_filter = tag.lower().strip() if tag else None

        for path, path_item in spec.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                    continue
                if not isinstance(operation, dict):
                    continue

                tags = operation.get("tags") or []
                operation_id = operation.get("operationId") or f"{method}_{path}"
                summary = operation.get("summary") or ""

                if tag_filter and not any(str(t).lower() == tag_filter for t in tags):
                    continue

                if query:
                    haystack = " ".join([operation_id, summary, path, " ".join(map(str, tags))]).lower()
                    if query not in haystack:
                        continue

                found.append(
                    {
                        "operation_id": operation_id,
                        "method": method.upper(),
                        "path": path,
                        "summary": summary,
                        "tags": tags,
                    }
                )

        return {
            "count": len(found),
            "operations": sorted(found, key=lambda row: (row["path"], row["method"])),
        }

    async def call_operation(
        self,
        operation_id: str,
        *,
        path_params: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke any OpenAPI operation by operationId, enabling full endpoint coverage."""
        spec = await self.get_openapi_spec()

        selected_method: str | None = None
        selected_path: str | None = None
        selected_operation: dict[str, Any] | None = None
        for path, path_item in spec.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if not isinstance(operation, dict):
                    continue
                if operation.get("operationId") == operation_id:
                    selected_method = method.upper()
                    selected_path = path
                    selected_operation = operation
                    break
            if selected_method:
                break

        if not selected_method or not selected_path or not selected_operation:
            raise SupersetApiError(f"Unknown operation_id '{operation_id}'. Use superset_list_endpoints first.")

        rendered_path = selected_path
        expected_path_params = [
            p.get("name")
            for p in selected_operation.get("parameters", [])
            if isinstance(p, dict) and p.get("in") == "path"
        ]

        for parameter_name in expected_path_params:
            if not path_params or parameter_name not in path_params:
                raise SupersetApiError(f"Missing required path parameter '{parameter_name}'")
            rendered_path = rendered_path.replace(f"{{{parameter_name}}}", str(path_params[parameter_name]))

        if not rendered_path.startswith("/"):
            rendered_path = f"/{rendered_path}"

        return await self.request(
            selected_method,
            rendered_path,
            params=query_params,
            json_body=payload,
        )

    async def list_resource(self, resource: str, page: int = 0, page_size: int = 25) -> dict[str, Any]:
        return await self.request(
            "GET",
            f"/api/v1/{resource}/",
            params={"page": page, "page_size": page_size},
        )

    async def get_resource(self, resource: str, item_id: int) -> dict[str, Any]:
        return await self.request("GET", f"/api/v1/{resource}/{item_id}")

    async def create_resource(self, resource: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("POST", f"/api/v1/{resource}/", json_body=payload)

    async def update_resource(
        self,
        resource: str,
        item_id: int,
        payload: dict[str, Any],
        *,
        partial: bool = True,
    ) -> dict[str, Any]:
        method = "PUT" if not partial else "PATCH"
        return await self.request(method, f"/api/v1/{resource}/{item_id}", json_body=payload)

    async def delete_resource(self, resource: str, item_id: int) -> dict[str, Any]:
        return await self.request("DELETE", f"/api/v1/{resource}/{item_id}")
