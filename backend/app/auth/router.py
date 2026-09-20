"""Authentication API routes."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict

from fastapi import APIRouter, HTTPException, Request, status

from app.auth.schemas import AccessTokenResponse, LoginRequest, RefreshRequest, TokenResponse
from app.config import get_settings
from app.auth.service import (
    CredentialsNotConfiguredError,
    InvalidCredentialsError,
    InvalidTokenError,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    validate_refresh_token,
)

_login_attempts: OrderedDict[str, list[float]] = OrderedDict()
_ATTEMPT_WINDOW_SECONDS = 60
_MAX_ATTEMPTS_PER_WINDOW = 10
_MAX_TRACKED_CLIENTS = 4096

router = APIRouter(prefix="/api/auth", tags=["auth"])


def client_identity(request: Request | None) -> str:
    """Identify the caller for throttling.

    X-Forwarded-For is attacker-controlled unless a proxy is known to rewrite it,
    so it is only consulted when RALPH_TRUSTED_PROXY_HOPS says how many trailing
    entries that proxy appends. Otherwise every caller behind a proxy would share
    one bucket and ten failures would lock out everyone.
    """
    if request is None:
        return "unknown"
    hops = get_settings().trusted_proxy_hops
    if hops:
        forwarded = [part.strip() for part in
                     request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
        if len(forwarded) >= hops:
            return forwarded[-hops]
    return request.client.host if request.client else "unknown"


def _recent_attempts(address: str) -> list[float]:
    cutoff = time.monotonic() - _ATTEMPT_WINDOW_SECONDS
    return [stamp for stamp in _login_attempts.get(address, []) if stamp > cutoff]


def _record_failure(address: str) -> None:
    _login_attempts[address] = [*_recent_attempts(address), time.monotonic()]
    _login_attempts.move_to_end(address)
    while len(_login_attempts) > _MAX_TRACKED_CLIENTS:
        _login_attempts.popitem(last=False)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request = None) -> TokenResponse:
    address = client_identity(request)
    if len(_recent_attempts(address)) >= _MAX_ATTEMPTS_PER_WINDOW:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in one minute.",
                            headers={"Retry-After": str(_ATTEMPT_WINDOW_SECONDS)})
    try:
        credentials = await asyncio.to_thread(authenticate_user, payload.username, payload.password)
    except CredentialsNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credentials not configured",
        ) from exc
    except InvalidCredentialsError as exc:
        # Only failures consume the budget, so repeated successful sign-ins
        # from one address are never throttled.
        _record_failure(address)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from exc

    _login_attempts.pop(address, None)
    return TokenResponse(
        access_token=create_access_token(credentials.username),
        refresh_token=create_refresh_token(credentials.username),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(payload: RefreshRequest) -> AccessTokenResponse:
    try:
        token_payload = validate_refresh_token(payload.refresh_token)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) from exc

    return AccessTokenResponse(access_token=create_access_token(token_payload.sub))
