"""Authentication API routes."""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict

from fastapi import APIRouter, HTTPException, Request, status

from app.auth.schemas import AccessTokenResponse, LoginRequest, RefreshRequest, TokenResponse
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

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request = None) -> TokenResponse:
    if request is not None:
        address = request.client.host if request.client else "unknown"
        cutoff = time.monotonic() - 60
        attempts = [stamp for stamp in _login_attempts.get(address, []) if stamp > cutoff]
        if len(attempts) >= 10:
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again in one minute.",
                                headers={"Retry-After": "60"})
        _login_attempts[address] = [*attempts, time.monotonic()]
        _login_attempts.move_to_end(address)
        if len(_login_attempts) > 4096:
            _login_attempts.popitem(last=False)
    try:
        credentials = await asyncio.to_thread(authenticate_user, payload.username, payload.password)
    except CredentialsNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credentials not configured",
        ) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from exc

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
