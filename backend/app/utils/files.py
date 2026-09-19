"""Atomic file persistence and bounded reads shared by runner and API."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_last_jsonl_record(path: Path) -> dict | None:
    """Read backwards until a complete JSON record is found, without a line-size cap."""
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            position = handle.tell()
            buffer = b""
            while position:
                size = min(65536, position)
                position -= size
                handle.seek(position)
                buffer = handle.read(size) + buffer
                lines = buffer.split(b"\n")
                complete = lines if position == 0 else lines[1:]
                for line in reversed(complete):
                    if not line.strip():
                        continue
                    try:
                        value = json.loads(line)
                    except (ValueError, UnicodeDecodeError):
                        continue
                    if isinstance(value, dict):
                        return value
                buffer = lines[0]
    except OSError:
        pass
    return None


def contained_path(root: Path, relative: str) -> Path:
    """Reject traversal and symlinks that resolve outside the project."""
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError("File path must stay inside the project")
    return path
