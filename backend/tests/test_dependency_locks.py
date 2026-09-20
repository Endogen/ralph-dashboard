"""Verify lock checks against real resolver behavior and a local package source."""

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest


def test_lock_check_preserves_pins_but_rejects_incompatible_manifest(tmp_path, monkeypatch):
    if shutil.which("uv") is None:
        pytest.skip("uv is required for the lockfile workflow test")
    (tmp_path / "backend").mkdir()
    (tmp_path / "scripts").mkdir()
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    script = tmp_path / "scripts/update_locks.sh"
    shutil.copyfile(Path(__file__).resolve().parents[2] / "scripts/update_locks.sh", script)
    project = tmp_path / "backend/pyproject.toml"
    project.write_text(
        '[project]\nname="lock-fixture"\nversion="1"\nrequires-python=">=3.12"\n'
        'dependencies=["review-fixture>=1"]\n[project.optional-dependencies]\ndev=[]\n'
    )
    monkeypatch.setenv("UV_NO_INDEX", "true")
    monkeypatch.setenv("UV_FIND_LINKS", str(wheels))

    def wheel(version):
        with zipfile.ZipFile(wheels / f"review_fixture-{version}-py3-none-any.whl", "w") as archive:
            info = f"review_fixture-{version}.dist-info"
            archive.writestr(
                f"{info}/METADATA",
                f"Metadata-Version: 2.1\nName: review-fixture\nVersion: {version}\n",
            )
            archive.writestr(
                f"{info}/WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
            )
            archive.writestr(f"{info}/RECORD", "")

    def run(*arguments):
        return subprocess.run(arguments, cwd=tmp_path, text=True, capture_output=True, timeout=15)

    wheel("1.0")
    result = run("bash", str(script))
    assert result.returncode == 0, result.stderr
    locks = [tmp_path / "backend" / name for name in ("requirements.lock", "requirements-dev.lock")]
    originals = [lock.read_bytes() for lock in locks]
    wheel("2.0")
    result = run("bash", str(script), "--check")
    assert result.returncode == 0, result.stdout + result.stderr
    assert [lock.read_bytes() for lock in locks] == originals

    # The newer version really is available to a fresh resolution.
    result = run("uv", "pip", "compile", "backend/pyproject.toml", "--quiet")
    assert result.returncode == 0, result.stderr
    assert "review-fixture==2.0" in result.stdout

    project.write_text(project.read_text().replace("review-fixture>=1", "review-fixture>=2"))
    result = run("bash", str(script), "--check")
    assert result.returncode != 0
    assert "review-fixture==2.0" in result.stdout
    assert [lock.read_bytes() for lock in locks] == originals
