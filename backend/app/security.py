"""
Basic OWASP-aligned hardening, deliberately dependency-free (stdlib
`time`/`collections` only — no slowapi, no redis) so it works identically
in a single-instance deploy without extra infra. Swap the rate limiter
for a Redis-backed one before running multiple backend replicas, since
this one's state is per-process and won't be shared across them.

Covers, roughly:
- A03 Injection       -> SQLAlchemy ORM everywhere in this project, no
                          raw string-formatted SQL (see store.py/models.py)
- A04 Insecure Design  -> rate limiting on auth endpoints below
- A05 Security Misconfig -> security headers here; CORS from env, not "*"
- A07 Auth Failures    -> PBKDF2 password hashing + short-lived JWTs (auth.py)
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "0"  # modern browsers: CSP is the real defense, this header is legacy/no-op
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window limiter: `limit` requests per `window_seconds` per
    (client IP, path-prefix). Only applied to the path prefixes you pass
    in -- leave auth endpoints covered, leave read-only GETs alone.
    """

    def __init__(self, app, limited_prefixes: tuple[str, ...], limit: int = 20, window_seconds: int = 60):
        super().__init__(app)
        self.limited_prefixes = limited_prefixes
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.limited_prefixes):
            client_ip = request.client.host if request.client else "unknown"
            key = f"{client_ip}:{path}"
            now = time.time()
            window = self._hits[key]
            while window and window[0] < now - self.window_seconds:
                window.popleft()
            if len(window) >= self.limit:
                return Response(
                    content='{"detail":"Too many requests -- slow down and try again shortly."}',
                    status_code=429,
                    media_type="application/json",
                )
            window.append(now)
        return await call_next(request)


def get_allowed_origins() -> list[str]:
    """
    CORS origins from env, comma-separated
    (ALLOWED_ORIGINS=https://myapp.vercel.app,https://myapp.com).
    Falls back to "*" ONLY if nothing is set, which is fine for a
    hackathon demo and wrong for anything handling real user data --
    set ALLOWED_ORIGINS before that.
    """
    raw = os.environ.get("ALLOWED_ORIGINS", "").strip()
    if not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]
