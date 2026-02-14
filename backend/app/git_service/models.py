"""Git API models."""

from __future__ import annotations

from pydantic import BaseModel


class GitCommitSummary(BaseModel):
    hash: str
    author: str
    date: str
    message: str
    files_changed: int
    insertions: int
    deletions: int


class GitCommitDiff(BaseModel):
    hash: str
    diff: str
