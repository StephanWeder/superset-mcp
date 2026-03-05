# Coding and MCP Conventions

This project follows conventions that keep MCP tools safe, composable, and predictable for AI clients.

## Python conventions

1. **Type hints everywhere**
   - All public functions include precise type annotations.
   - Return structured `dict[str, Any]` JSON-compatible payloads for MCP transport.

2. **Async I/O for network calls**
   - Use `httpx.AsyncClient` for Superset API interactions.
   - Keep tool functions async to avoid blocking the MCP host.

3. **Single-responsibility modules**
   - `config.py` only handles configuration loading/validation.
   - `client.py` handles HTTP/auth behavior and OpenAPI operation mapping.
   - `server.py` only defines MCP tools and server startup.

4. **Fail-fast configuration**
   - Required env vars are validated at startup.
   - Invalid setup should fail before the first tool invocation.

5. **Actionable errors**
   - Include HTTP method, endpoint, and response status/body in API errors.
   - Avoid swallowing exceptions; surface enough detail for operators.

## MCP conventions

1. **Stable, descriptive tool names**
   - Prefix tools with `superset_`.
   - Keep names verb-first where practical.

2. **Discovery-first complete coverage**
   - Use `superset_list_endpoints` for endpoint discovery.
   - Use `superset_call_endpoint` with `operation_id` for full documented API coverage.

3. **Structured parameters**
   - Tool arguments are explicit and typed.
   - Endpoint calls split `path_params`, `query_params`, and `payload` for clarity.

4. **Safe operations pattern**
   - Destructive operations are available but documented for human confirmation.
   - `superset_raw_api` is constrained to `/api/v1/` and `/swagger/`.

5. **Transport compatibility**
   - Server runs via stdio (`mcp.run()`), fitting Gemini CLI / MCP host process model.

## Superset API conventions

1. **Authenticate through `/api/v1/security/login`**.
2. **Send bearer token on each request**.
3. **Refresh/re-login on expiration/401**.
4. **Prefer OpenAPI `operationId` for resilient endpoint execution**.
5. **Keep convenience wrappers for common assets** (dashboard/chart/dataset/database).
