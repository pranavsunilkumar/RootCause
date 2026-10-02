"""
Authentication. Two deliberate choices, both to keep this dependency-
light and honest about what's actually tested:

- Password hashing uses stdlib hashlib.pbkdf2_hmac (NIST-approved,
  no bcrypt/passlib C-extension to install or fail to build on some
  hosts) instead of the more common passlib+bcrypt combo.
- JWTs use PyJWT, which is genuinely lightweight and pure-Python.

Set JWT_SECRET in production — the fallback below is fine for local
dev/demo only and is intentionally obvious about that.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import User

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-insecure-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_SECONDS = int(os.environ.get("JWT_EXPIRES_SECONDS", str(60 * 60 * 24 * 7)))  # 7 days

_PBKDF2_ITERATIONS = 260_000
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_b64, hash_b64 = encoded.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(username: str) -> str:
    payload = {"sub": username, "exp": int(time.time()) + JWT_EXPIRES_SECONDS, "iat": int(time.time())}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


RESET_TOKEN_EXPIRES_SECONDS = 15 * 60


def create_reset_token(username: str) -> str:
    payload = {"sub": username, "purpose": "password_reset", "exp": int(time.time()) + RESET_TOKEN_EXPIRES_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_reset_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("purpose") != "password_reset":
            return None
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def decode_access_token(token: str) -> Optional[str]:
    """Returns the username (sub claim) if the token is valid, else None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Strict dependency: 401s if there's no valid token. Use on routes
    that require login (register/me, and anything gamification-sensitive
    if you want to prevent fake leaderboard entries)."""
    username = decode_access_token(token) if token else None
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return user


def get_current_user_optional(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Optional[User]:
    """Soft dependency: returns None instead of 401ing, so existing routes
    keep working for anonymous/free-text learner ids while upgrading
    transparently for anyone who's logged in."""
    if not token:
        return None
    username = decode_access_token(token)
    if not username:
        return None
    return db.execute(select(User).where(User.username == username)).scalar_one_or_none()
