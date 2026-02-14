"""Pydantic schemas for auth API and token payloads."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class TokenPayload(BaseModel):
    sub: str
    type: Literal["access", "refresh"]
    exp: int


class Credentials(BaseModel):
    username: str = Field(min_length=1)
    password_hash: str = Field(min_length=1)
