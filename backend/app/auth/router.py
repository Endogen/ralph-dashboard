"""Authentication API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

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

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    try:
        credentials = authenticate_user(payload.username, payload.password)
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
