"""Bearer-token gate for mutating and privileged routes.

Production / REQUIRE_AUTH: TITAN_API_TOKEN is mandatory (process refuses to start
without it — see main lifespan). Development without a token: loopback-only
writes when ALLOW_UNAUTHENTICATED_LOOPBACK is true (default false).
ADB always requires a configured API token.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import TYPE_CHECKING, Annotated, Optional

if TYPE_CHECKING:
    from fastapi import Request

try:
    from fastapi import Header, HTTPException, Request
except ImportError:
    Header = object  # type: ignore
    HTTPException = Exception  # type: ignore
    Request = object  # type: ignore


def is_loopback(request: Request) -> bool:
    host = (request.client.host if getattr(request, "client", None) else "") or ""
    return host in ("127.0.0.1", "::1", "localhost", "testclient")


def tokens_equal(presented: str, expected: str) -> bool:
    """Constant-time compare via SHA-256 digests (safe for any unicode; no TypeError)."""
    if not isinstance(presented, str) or not isinstance(expected, str):
        return False
    if not presented or not expected:
        return False
    a = hashlib.sha256(presented.encode("utf-8")).digest()
    b = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(a, b)


def require_bearer(
    request: Request,
    authorization: Annotated[Optional[str], Header()] = None,
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
    if not tokens_equal(presented, token):
        raise HTTPException(status_code=401, detail="invalid_token")


def require_adb_enabled() -> None:
    from titan.config import settings

    if not settings.adb_enabled:
        raise HTTPException(
            status_code=403,
            detail="adb_disabled: set ADB_ENABLED=true to allow device capture",
        )
    if not settings.api_token:
        raise HTTPException(
            status_code=403,
            detail="adb_requires_token: set TITAN_API_TOKEN before enabling ADB",
        )


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def assert_boot_auth() -> None:
    from titan.config import settings

    if (settings.require_auth or settings.env == "production") and not settings.api_token:
        raise RuntimeError(
            "CELL TITAN refuse-to-start: CELL_TITAN_ENV=production or REQUIRE_AUTH=true "
            "requires TITAN_API_TOKEN to be set"
        )
