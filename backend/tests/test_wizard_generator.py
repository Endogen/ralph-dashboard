"""Tests for wizard LLM generator."""

from __future__ import annotations

import pytest

from app.wizard.generator import ApiKeyNotConfiguredError, generate_project_files
from app.wizard.schemas import GenerateRequest


@pytest.mark.anyio
async def test_generate_raises_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    request = GenerateRequest(
        project_name="test-project",
        project_description="A simple test project",
    )

    with pytest.raises(ApiKeyNotConfiguredError):
        await generate_project_files(request)
