"""Configuration helpers for Superset MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_quotes(value.strip())
        if key:
            values[key] = value
    return values


def _load_superset_env_fallbacks() -> None:
    """Load env values from files for hosts that don't pass shell rc vars.

    Priority order (earlier wins):
    1) Existing process env values
    2) SUPERSET_ENV_FILE if set
    3) ./.superset-mcp.env
    4) ./.env
    5) ~/.config/superset-mcp/env
    """

    candidates: list[Path] = []
    explicit = os.getenv("SUPERSET_ENV_FILE", "").strip()
    if explicit:
        candidates.append(Path(explicit).expanduser())

    cwd = Path.cwd()
    candidates.extend([cwd / ".superset-mcp.env", cwd / ".env", Path.home() / ".config/superset-mcp/env"])

    merged: dict[str, str] = {}
    for path in candidates:
        merged.update(_read_env_file(path))

    for key, value in merged.items():
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class SupersetSettings:
    """Runtime configuration loaded from environment variables."""

    base_url: str
    username: str
    password: str
    provider: str = "db"
    refresh_seconds: int = 1200
    verify_ssl: bool = True

    @classmethod
    def from_env(cls) -> "SupersetSettings":
        """Load settings from environment and validate required fields."""
        _load_superset_env_fallbacks()

        base_url = os.getenv("SUPERSET_BASE_URL", "").strip().rstrip("/")
        username = os.getenv("SUPERSET_USERNAME", "").strip()
        password = os.getenv("SUPERSET_PASSWORD", "")
        provider = os.getenv("SUPERSET_AUTH_PROVIDER", "db").strip() or "db"
        refresh_seconds = int(os.getenv("SUPERSET_TOKEN_REFRESH_SECONDS", "1200"))
        verify_ssl_raw = os.getenv("SUPERSET_VERIFY_SSL", "true").lower().strip()
        verify_ssl = verify_ssl_raw in {"1", "true", "yes", "on"}

        missing = []
        if not base_url:
            missing.append("SUPERSET_BASE_URL")
        if not username:
            missing.append("SUPERSET_USERNAME")
        if not password:
            missing.append("SUPERSET_PASSWORD")

        if missing:
            details = ", ".join(missing)
            raise ValueError(f"Missing required env vars: {details}")

        return cls(
            base_url=base_url,
            username=username,
            password=password,
            provider=provider,
            refresh_seconds=refresh_seconds,
            verify_ssl=verify_ssl,
        )
