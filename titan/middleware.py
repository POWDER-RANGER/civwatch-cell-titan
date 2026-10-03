"""Hardening middleware: request size limit, security headers, simple rate limit."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Cell-Titan"] = "defensive-only"
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_bytes: int = 65_536) -> None:
        super().__init__(app)
        self.max_body_bytes = max_body_bytes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > self.max_body_bytes:
                    return JSONResponse({"error": "payload_too_large"}, status_code=413)
            except ValueError:
                return JSONResponse({"error": "invalid_content_length"}, status_code=400)
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window per-client limiter for mutating routes only."""

    def __init__(self, app, limit: int = 60, window_sec: float = 60.0) -> None:
        super().__init__(app)
        self.limit = limit
        self.window = window_sec
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return await call_next(request)
        if request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        q = self._hits[client]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return JSONResponse(
                {"error": "rate_limited", "retry_after_sec": int(self.window)},
                status_code=429,
            )
        q.append(now)
        return await call_next(request)
