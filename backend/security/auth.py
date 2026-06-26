"""
Lumina Security — JWT Authentication
Provides token creation, verification, and FastAPI dependencies.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config.settings import settings
import logging

logger = logging.getLogger(__name__)

_http_bearer = HTTPBearer(auto_error=False)

# ── Demo user store (swap for a real DB in production) ──────────────────────
DEMO_USERS: Dict[str, Dict[str, str]] = {
    "lumina": {"password": "lumina123", "role": "admin"},
    "demo":   {"password": "demo",      "role": "user"},
    "guest":  {"password": "guest",     "role": "guest"},
}


# ── Token helpers ────────────────────────────────────────────────────────────

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Mint a signed JWT access token."""
    payload = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload.update({"exp": expire, "iat": datetime.utcnow(), "iss": "lumina"})
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT; returns payload or None."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        logger.debug(f"JWT verification failed: {exc}")
        return None


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Validate username/password against the user store."""
    user = DEMO_USERS.get(username)
    if user and user["password"] == password:
        return {"username": username, "role": user["role"]}
    return None


# ── FastAPI dependencies ─────────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_http_bearer),
) -> Dict[str, Any]:
    """Optional auth — falls back to guest if no / invalid token."""
    if credentials is None:
        return {"username": "guest", "role": "guest"}
    payload = verify_token(credentials.credentials)
    if payload is None:
        return {"username": "guest", "role": "guest"}
    return {"username": payload.get("sub", "unknown"), "role": payload.get("role", "user")}


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_http_bearer),
) -> Dict[str, Any]:
    """Strict auth — raises HTTP 401 if unauthenticated."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"username": payload.get("sub"), "role": payload.get("role", "user")}
