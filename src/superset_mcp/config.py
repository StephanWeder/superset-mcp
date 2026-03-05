"""Configuration helpers for Superset MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass


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
