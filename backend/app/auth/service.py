"""Authentication primitives: credential loading, password hashing, JWT handling."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import bcrypt
from jose import JWTError, jwt
from pydantic import ValidationError

from app.auth.schemas import Credentials, TokenPayload
from app.config import get_settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthError(Exception):
    """Base exception for auth-related failures."""


class CredentialsNotConfiguredError(AuthError):
    """Raised when no credentials file is configured or present."""


class InvalidCredentialsError(AuthError):
    """Raised when username/password validation fails."""


class InvalidTokenError(AuthError):
    """Raised when JWT verification fails."""


class AuthConfigurationError(AuthError):
    """Raised when auth credentials file is malformed."""


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify plaintext password against stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _parse_credentials_content(content: str) -> dict[str, str]:
    """Parse a tiny YAML-like key:value credentials document."""
    parsed: dict[str, str] = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        parsed[key.strip()] = value.strip().strip("'").strip('"')
    return parsed


def load_credentials(credentials_file: Path | None = None) -> Credentials | None:
    """Load username and password hash from the configured credentials file."""
    path = credentials_file or get_settings().credentials_file
    if not path.exists() or not path.is_file():
        return None

    parsed = _parse_credentials_content(path.read_text(encoding="utf-8"))
    try:
        return Credentials.model_validate(parsed)
    except ValidationError as exc:
        raise AuthConfigurationError("Malformed credentials file") from exc


def authenticate_user(
    username: str, password: str, credentials_file: Path | None = None
) -> Credentials:
    """Validate provided credentials against configured credentials file."""
    credentials = load_credentials(credentials_file)
    if credentials is None:
        raise CredentialsNotConfiguredError("Credentials are not configured")

    if credentials.username != username:
        raise InvalidCredentialsError("Invalid username or password")
    if not verify_password(password, credentials.password_hash):
        raise InvalidCredentialsError("Invalid username or password")
    return credentials


def _build_token(subject: str, token_type: Literal["access", "refresh"], expires: timedelta) -> str:
    expires_at = datetime.now(timezone.utc) + expires
    payload = {
        "sub": subject,
        "type": token_type,
        "exp": expires_at,
    }
    return jwt.encode(payload, get_settings().secret_key, algorithm=ALGORITHM)


def create_access_token(subject: str) -> str:
    """Create a signed short-lived access token."""
    return _build_token(subject, "access", timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(subject: str) -> str:
    """Create a signed longer-lived refresh token."""
    return _build_token(subject, "refresh", timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(
    token: str, expected_type: Literal["access", "refresh"] | None = None
) -> TokenPayload:
    """Decode and validate a JWT token."""
    secret_key = get_settings().secret_key
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise InvalidTokenError("Invalid token") from exc

    try:
        token_payload = TokenPayload.model_validate(payload)
    except ValidationError as exc:
        raise InvalidTokenError("Invalid token payload") from exc

    if expected_type is not None and token_payload.type != expected_type:
        raise InvalidTokenError("Unexpected token type")

    return token_payload


def validate_access_token(token: str) -> TokenPayload:
    """Validate an access token and return the parsed payload."""
    return decode_token(token, expected_type="access")


def validate_refresh_token(token: str) -> TokenPayload:
    """Validate a refresh token and return the parsed payload."""
    return decode_token(token, expected_type="refresh")
