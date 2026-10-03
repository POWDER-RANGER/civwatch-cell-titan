"""Bearer-token gate for mutating and privileged routes.

Design:
- If TITAN_API_TOKEN is unset/empty: write routes work on loopback only when
  ALLOW_UNAUTHENTICATED_LOOPBACK is true (default in development).
- Non-loopback clients always need a matching Bearer token when a token is configured.
- When REQUIRE_AUTH=true (or production env), token is mandatory for protected routes
  even on loopback.
- ADB routes additionally require ADB_ENABLED=true.
"""
from __future__ import annotations

import hmac
import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Request


def is_loopback(request: Request) -> bool:
    host = (request.client.host if request.client else "") or ""
    return host in ("127.0.0.1", "::1", "localhost", "testclient")


def token_configured() -> bool:
    from titan.config import settings

    return bool(settings.api_token)


def require_bearer(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    from titan.config import settings

    token = settings.api_token
    require = settings.require_auth or settings.env == "production"

    if not token:
        if require:
            raise HTTPException(
                status_code=503,
                detail="auth_misconfigured: TITAN_API_TOKEN required when REQUIRE_AUTH/production",
            )
        if settings.allow_unauthenticated_loopback and is_loopback(request):
            return
        raise HTTPException(
            status_code=401,
            detail="unauthorized: set TITAN_API_TOKEN and send Authorization: Bearer <token>",
        )

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    presented = authorization.split(" ", 1)[1].strip()
    if not presented or not hmac.compare_digest(presented, token):
        raise HTTPException(status_code=401, detail="invalid_token")


def require_adb_enabled() -> None:
    from titan.config import settings

    if not settings.adb_enabled:
        raise HTTPException(
            status_code=403,
            detail="adb_disabled: set ADB_ENABLED=true to allow device capture",
        )


def generate_token() -> str:
    return secrets.token_urlsafe(32)
