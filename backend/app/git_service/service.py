"""Git inspection services."""

from __future__ import annotations

from datetime import UTC, datetime
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
    """Return commit summaries for a project repository."""
    project_path = await _resolve_project_path(project_id)
    repo = _open_repo(project_path)

    commits = list(repo.iter_commits("HEAD", max_count=limit, skip=offset))
    result: list[GitCommitSummary] = []
    for commit in commits:
        total_stats = commit.stats.total
        result.append(
            GitCommitSummary(
                hash=commit.hexsha[:7],
                author=commit.author.name,
                date=datetime.fromtimestamp(commit.committed_date, tz=UTC).isoformat(),
                message=commit.message.strip(),
                files_changed=int(total_stats.get("files", 0)),
                insertions=int(total_stats.get("insertions", 0)),
                deletions=int(total_stats.get("deletions", 0)),
            )
        )
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
