"""Regressions for the issues found in the reliability-overhaul review."""
from __future__ import annotations

import asyncio
import hashlib
import os
import time
from pathlib import Path

import pytest

from app.auth import router as auth_router
from app.utils.files import atomic_write, atomic_write_bytes
from app.utils.process import process_lock, prune_stale_locks
from app.wizard.schemas import CreateRequest, GeneratedFile
from app.wizard.service import _prepare_project, preview_project


def _create_request(project_dir: Path, files, expected_versions=None) -> CreateRequest:
    return CreateRequest(
        project_name=project_dir.name,
        project_mode="existing",
        existing_project_path=str(project_dir),
        files=[GeneratedFile(path=path, content=content) for path, content in files],
        expected_versions=expected_versions or {},
    )


# --- Blocking: preview and prepare must hash identical bytes -----------------

@pytest.mark.anyio
async def test_preview_version_matches_prepare_for_crlf_file(tmp_path, monkeypatch):
    """A CRLF file must not read as 'changed since preview'."""
    from app.config import get_settings

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(tmp_path))
    get_settings.cache_clear()
    project = tmp_path / "crlf-project"
    project.mkdir()
    (project / ".git").mkdir()
    (project / "AGENTS.md").write_bytes(b"alpha\r\nbeta\r\n")

    request = _create_request(project, [("AGENTS.md", "replacement\n")])
    preview = await preview_project(request)

    on_disk = hashlib.sha256((project / "AGENTS.md").read_bytes()).hexdigest()
    assert preview["versions"]["AGENTS.md"] == on_disk

    # The same versions must satisfy _prepare_project's re-check.
    accepted = _create_request(project, [("AGENTS.md", "replacement\n")],
                               expected_versions=preview["versions"])
    await asyncio.to_thread(_prepare_project, accepted, project, False)
    assert (project / "AGENTS.md").read_bytes() == b"replacement\n"


@pytest.mark.anyio
async def test_preview_survives_non_utf8_file(tmp_path, monkeypatch):
    """A latin-1 byte sequence must not raise out of preview."""
    from app.config import get_settings

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(tmp_path))
    get_settings.cache_clear()
    project = tmp_path / "binary-project"
    project.mkdir()
    (project / ".git").mkdir()
    (project / "AGENTS.md").write_bytes(b"caf\xe9 not utf-8\n")

    preview = await preview_project(_create_request(project, [("AGENTS.md", "new\n")]))
    assert preview["versions"]["AGENTS.md"] == hashlib.sha256(b"caf\xe9 not utf-8\n").hexdigest()
    assert "�" in preview["files"][0]["previous"]


@pytest.mark.anyio
async def test_rollback_restores_original_bytes(tmp_path, monkeypatch):
    """A failed prepare must restore CRLF exactly, not an LF-normalised copy."""
    from app.config import get_settings
    from app.wizard import service as wizard_service

    monkeypatch.setenv("RALPH_PROJECT_DIRS", str(tmp_path))
    get_settings.cache_clear()
    project = tmp_path / "rollback-project"
    project.mkdir()
    (project / "AGENTS.md").write_bytes(b"original\r\nlines\r\n")

    def _boom(_project_dir):
        raise RuntimeError("git unavailable")

    monkeypatch.setattr(wizard_service, "_ensure_git_repository", _boom)
    with pytest.raises(RuntimeError):
        await asyncio.to_thread(
            _prepare_project, _create_request(project, [("AGENTS.md", "rewritten\n")]), project, False
        )
    assert (project / "AGENTS.md").read_bytes() == b"original\r\nlines\r\n"


def test_atomic_write_bytes_preserves_content(tmp_path):
    target = tmp_path / "file.bin"
    atomic_write_bytes(target, b"\r\n\x00\xff")
    assert target.read_bytes() == b"\r\n\x00\xff"
    atomic_write(target, "text\n")
    assert target.read_bytes() == b"text\n"


# --- Login throttling --------------------------------------------------------

def test_only_failed_logins_consume_the_budget():
    auth_router._login_attempts.clear()
    for _ in range(auth_router._MAX_ATTEMPTS_PER_WINDOW):
        auth_router._record_failure("10.0.0.1")
    assert len(auth_router._recent_attempts("10.0.0.1")) >= auth_router._MAX_ATTEMPTS_PER_WINDOW
    auth_router._login_attempts.pop("10.0.0.1", None)
    assert auth_router._recent_attempts("10.0.0.1") == []


def test_forwarded_for_ignored_unless_proxy_is_trusted(monkeypatch):
    from app.config import get_settings

    class FakeClient:
        host = "127.0.0.1"

    class FakeRequest:
        client = FakeClient()
        headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}

    monkeypatch.delenv("RALPH_TRUSTED_PROXY_HOPS", raising=False)
    get_settings.cache_clear()
    assert auth_router.client_identity(FakeRequest()) == "127.0.0.1"

    monkeypatch.setenv("RALPH_TRUSTED_PROXY_HOPS", "1")
    get_settings.cache_clear()
    assert auth_router.client_identity(FakeRequest()) == "5.6.7.8"
    get_settings.cache_clear()


# --- Lock pruning ------------------------------------------------------------

def test_prune_stale_locks_keeps_fresh_and_held_locks(tmp_path):
    stale = tmp_path / "stale.lock"
    stale.write_text("")
    os.utime(stale, (time.time() - 30 * 24 * 3600,) * 2)
    fresh = tmp_path / "fresh.lock"
    fresh.write_text("")

    with process_lock(tmp_path, "held.lock"):
        prune_stale_locks(tmp_path)
        assert not stale.exists()
        assert fresh.exists()
        assert (tmp_path / "held.lock").exists()
