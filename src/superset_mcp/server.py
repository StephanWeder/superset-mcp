"""MCP server exposing Superset API operations for AI assistants."""

from __future__ import annotations

import atexit
from typing import Any, Literal

from fastmcp import FastMCP

from superset_mcp.client import SupersetApiError, SupersetClient
from superset_mcp.config import SupersetSettings

RESOURCE_NAME = Literal[
    "dashboard",
    "chart",
    "dataset",
    "database",
    "saved_query",
    "tag",
]

settings = SupersetSettings.from_env()
client = SupersetClient(settings)

mcp = FastMCP(
    "superset-api",
    instructions=(
        "Use superset_list_endpoints to discover operations and superset_call_endpoint "
        "for full API coverage. For deletes/overwrites, require human confirmation first."
    ),
)


@atexit.register
def _close_client_sync() -> None:
    """Best-effort shutdown for httpx async client."""
    try:
        import asyncio

        asyncio.run(client.close())
    except RuntimeError:
        pass


@mcp.tool()
async def superset_health() -> dict[str, Any]:
    """Check Superset API health endpoint."""
    return await client.request("GET", "/api/v1/health")


@mcp.tool()
async def superset_list_endpoints(
    tag: str | None = None,
    search: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """List Superset OpenAPI operations (operation_id + method + path)."""
    return await client.list_operations(tag=tag, search=search, force_refresh=force_refresh)


@mcp.tool()
async def superset_call_endpoint(
    operation_id: str,
    path_params: dict[str, Any] | None = None,
    query_params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call any Superset endpoint by operation_id from the OpenAPI spec."""
    return await client.call_operation(
        operation_id,
        path_params=path_params,
        query_params=query_params,
        payload=payload,
    )


@mcp.tool()
async def superset_list_resources(
    resource: RESOURCE_NAME,
    page: int = 0,
    page_size: int = 25,
) -> dict[str, Any]:
    """List dashboards/charts/datasets/databases etc."""
    return await client.list_resource(resource, page=page, page_size=page_size)


@mcp.tool()
async def superset_get_resource(resource: RESOURCE_NAME, item_id: int) -> dict[str, Any]:
    """Get details of a single resource by id."""
    return await client.get_resource(resource, item_id)


@mcp.tool()
async def superset_create_resource(resource: RESOURCE_NAME, payload: dict[str, Any]) -> dict[str, Any]:
    """Create resource in Superset. Payload must match Superset API schema."""
    return await client.create_resource(resource, payload)


@mcp.tool()
async def superset_update_resource(
    resource: RESOURCE_NAME,
    item_id: int,
    payload: dict[str, Any],
    partial: bool = True,
) -> dict[str, Any]:
    """Update existing resource via PATCH (default) or PUT."""
    return await client.update_resource(resource, item_id, payload, partial=partial)


@mcp.tool()
async def superset_delete_resource(resource: RESOURCE_NAME, item_id: int) -> dict[str, Any]:
    """Delete a resource by id."""
    return await client.delete_resource(resource, item_id)


@mcp.tool()
async def superset_create_dashboard(
    dashboard_title: str,
    slug: str | None = None,
    owners: list[int] | None = None,
    published: bool = False,
    json_metadata: str | None = None,
) -> dict[str, Any]:
    """Convenience tool for creating a dashboard."""
    payload: dict[str, Any] = {
        "dashboard_title": dashboard_title,
        "published": published,
    }
    if slug:
        payload["slug"] = slug
    if owners:
        payload["owners"] = owners
    if json_metadata:
        payload["json_metadata"] = json_metadata
    return await client.create_resource("dashboard", payload)


@mcp.tool()
async def superset_create_chart(
    slice_name: str,
    viz_type: str,
    datasource_id: int,
    datasource_type: str = "table",
    params: str = "{}",
    owners: list[int] | None = None,
) -> dict[str, Any]:
    """Convenience tool for creating a chart/slice."""
    payload: dict[str, Any] = {
        "slice_name": slice_name,
        "viz_type": viz_type,
        "datasource_id": datasource_id,
        "datasource_type": datasource_type,
        "params": params,
    }
    if owners:
        payload["owners"] = owners
    return await client.create_resource("chart", payload)


@mcp.tool()
async def superset_execute_sql(
    database_id: int,
    sql: str,
    schema: str | None = None,
    run_async: bool = True,
    catalog: str | None = None,
) -> dict[str, Any]:
    """Execute SQL Lab query in Superset."""
    payload: dict[str, Any] = {
        "database_id": database_id,
        "sql": sql,
        "runAsync": run_async,
    }
    if schema:
        payload["schema"] = schema
    if catalog:
        payload["catalog"] = catalog

    return await client.request("POST", "/api/v1/sqllab/execute/", json_body=payload)


@mcp.tool()
async def superset_raw_api(
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Escape hatch for custom calls; path must start with '/api/v1/' or '/swagger/'."""
    if not (path.startswith("/api/v1/") or path.startswith("/swagger/")):
        raise SupersetApiError("path must start with '/api/v1/' or '/swagger/'")
    return await client.request(method, path, params=params, json_body=payload)


def main() -> None:
    """Entry point for CLI script."""
    mcp.run()


if __name__ == "__main__":
    main()
