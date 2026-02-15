"""Git inspection services."""

from __future__ import annotations

import asyncio
from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, Repo

from app.git_service.models import GitCommitDiff, GitCommitSummary
from app.projects.service import get_project_detail


class GitServiceError(Exception):
    """Base git service error."""


class GitProjectNotFoundError(GitServiceError):
    """Raised when project id cannot be resolved."""


class GitRepositoryNotFoundError(GitServiceError):
    """Raised when project path is not a git repository."""


class GitCommitNotFoundError(GitServiceError):
    """Raised when requested commit hash does not exist."""


async def _resolve_project_path(project_id: str) -> Path:
    project = await get_project_detail(project_id)
    if project is None:
        raise GitProjectNotFoundError(f"Project not found: {project_id}")
    return project.path


def _open_repo(project_path: Path) -> Repo:
    try:
        return Repo(project_path)
    except InvalidGitRepositoryError as exc:
        raise GitRepositoryNotFoundError(f"Not a git repository: {project_path}") from exc


async def get_git_log(project_id: str, limit: int = 50, offset: int = 0) -> list[GitCommitSummary]:
    """Return commit summaries for a project repository.

    Uses ``git log --shortstat`` in a single subprocess call instead of
    computing per-commit stats via GitPython (which spawns one subprocess
    per commit and can be very slow for large repos).
    """
    import re
    from asyncio.subprocess import PIPE

    project_path = await _resolve_project_path(project_id)
    _open_repo(project_path)

    separator = "---RALPH_SEP---"
    fmt = f"%H{separator}%an{separator}%aI{separator}%s"
    process = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(project_path),
        "log",
        f"--max-count={limit}",
        f"--skip={offset}",
        f"--format={fmt}",
        "--shortstat",
        stdout=PIPE,
        stderr=PIPE,
    )
    stdout, _ = await process.communicate()
    if process.returncode != 0:
        return []

    raw = stdout.decode("utf-8", errors="replace")
    stat_re = re.compile(
        r"(\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?"
    )

    result: list[GitCommitSummary] = []
    current: dict | None = None
    for line in raw.splitlines():
        if separator in line:
            if current is not None:
                result.append(GitCommitSummary(**current))
            parts = line.split(separator, 3)
            current = {
                "hash": parts[0][:7],
                "author": parts[1],
                "date": parts[2],
                "message": parts[3] if len(parts) > 3 else "",
                "files_changed": 0,
                "insertions": 0,
                "deletions": 0,
            }
        elif current is not None:
            m = stat_re.search(line)
            if m:
                current["files_changed"] = int(m.group(1) or 0)
                current["insertions"] = int(m.group(2) or 0)
                current["deletions"] = int(m.group(3) or 0)
    if current is not None:
        result.append(GitCommitSummary(**current))
    return result


async def get_git_diff(project_id: str, commit_hash: str) -> GitCommitDiff:
    """Return unified diff text for a commit hash."""
    project_path = await _resolve_project_path(project_id)
    repo = _open_repo(project_path)
    try:
        commit = repo.commit(commit_hash)
    except Exception as exc:  # GitPython raises different exceptions per resolution path
        raise GitCommitNotFoundError(f"Commit not found: {commit_hash}") from exc

    try:
        diff_text = repo.git.show(commit.hexsha, format="", no_color=True)
    except GitCommandError as exc:
        raise GitCommitNotFoundError(f"Commit not found: {commit_hash}") from exc

    return GitCommitDiff(hash=commit.hexsha[:7], diff=diff_text)
