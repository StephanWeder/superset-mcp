# Superset MCP Server (Python)

MCP server that exposes Apache Superset REST APIs as tools so AI clients (including Gemini CLI MCP integrations) can create and manage:

- databases
- datasets
- charts
- dashboards
- saved queries
- any documented endpoint via operation-based endpoint calling

It is designed for stdio transport so it can run as an MCP extension process.

## Endpoint coverage answer (important)

Yes, this server now supports **full Superset API endpoint coverage** through two discovery-first tools:

1. `superset_list_endpoints` — reads Superset OpenAPI (`/swagger/v1` fallback `/api/v1/_openapi`) and lists callable operations.
2. `superset_call_endpoint` — executes any endpoint by `operation_id` with path/query/body inputs.

This means the AI can use clear operation IDs for all documented endpoints, not only pre-wrapped CRUD helpers.

## Features

- Token-based Superset authentication (`/api/v1/security/login`)
- OpenAPI-driven endpoint discovery and calling for complete docs coverage
- Generic CRUD tools for major resources
- Convenience tools for common workflows (create chart/dashboard, execute SQL)
- Raw API escape hatch for custom debugging calls
- Retries for authentication and strong error messages

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

Set environment variables before starting the server:

```bash
export SUPERSET_BASE_URL="https://your-superset-host"
export SUPERSET_USERNAME="admin"
export SUPERSET_PASSWORD="<password>"
# Optional:
export SUPERSET_AUTH_PROVIDER="db"
export SUPERSET_TOKEN_REFRESH_SECONDS="1200"
export SUPERSET_VERIFY_SSL="true"
```

## Run (stdio MCP server)

```bash
superset-mcp-server
```


## Install as Gemini CLI extension from GitHub

Yes. This repository now includes a `gemini-extension.json`, so you can install it similarly to workspace extensions:

```bash
gemini extensions install https://github.com/<your-org>/superset-mcp
```

After install, set the required Superset environment variables in your Gemini CLI environment (or extension runtime config):

- `SUPERSET_BASE_URL`
- `SUPERSET_USERNAME`
- `SUPERSET_PASSWORD`

The extension startup script (`scripts/start-mcp.sh`) will create a local virtualenv, install the package, and run `superset-mcp-server`.

## When Gemini CLI does not inherit your shell env (common on macOS)

Some Gemini extension hosts do not load `~/.zshrc`. This project supports file-based env loading:

1. Create `.superset-mcp.env` in the extension/project directory:

```bash
cat > .superset-mcp.env <<'ENV'
SUPERSET_BASE_URL=https://your-superset-host
SUPERSET_USERNAME=admin
SUPERSET_PASSWORD=your-password
SUPERSET_AUTH_PROVIDER=db
SUPERSET_TOKEN_REFRESH_SECONDS=1200
SUPERSET_VERIFY_SSL=true
ENV
```

2. Restart Gemini CLI.

`start-mcp.sh` auto-loads `.superset-mcp.env` (fallback `.env`) before launching the server. You can also set `SUPERSET_ENV_FILE=/absolute/path/to/file` to point the Python server at a custom env file.

## Gemini CLI MCP integration

Add a server entry to your Gemini CLI MCP configuration (path may vary by install):

```json
{
  "mcpServers": {
    "superset": {
      "command": "superset-mcp-server",
      "env": {
        "SUPERSET_BASE_URL": "https://your-superset-host",
        "SUPERSET_USERNAME": "admin",
        "SUPERSET_PASSWORD": "your-password",
        "SUPERSET_AUTH_PROVIDER": "db",
        "SUPERSET_TOKEN_REFRESH_SECONDS": "1200",
        "SUPERSET_VERIFY_SSL": "true"
      }
    }
  }
}
```

Then restart Gemini CLI and you should see Superset tools available for agent workflows.

## Recommended AI workflow

1. Call `superset_list_endpoints` with optional `tag` or `search`.
2. Pick the matching `operation_id`.
3. Call `superset_call_endpoint` with `path_params`, `query_params`, and `payload`.
4. Use convenience helpers only when they match your intent.

## Available MCP tools

- `superset_health`
- `superset_list_endpoints`
- `superset_call_endpoint`
- `superset_list_resources`
- `superset_get_resource`
- `superset_create_resource`
- `superset_update_resource`
- `superset_delete_resource`
- `superset_create_dashboard`
- `superset_create_chart`
- `superset_execute_sql`
- `superset_raw_api`

## Security notes

- Prefer a dedicated Superset service account with least privileges.
- Rotate credentials and inject via secure secret manager.
- For destructive operations (`delete`, broad `patch`), require human confirmation in your AI workflows.

## Development

```bash
pip install -e .[dev]
ruff check .
pytest
```

See `docs/conventions.md` for coding and MCP conventions used in this project.
