"""CLI utility for initializing dashboard auth credentials."""

from __future__ import annotations

import argparse
import getpass
from pathlib import Path
from stat import S_IRUSR, S_IWUSR

from app.auth.service import hash_password
from app.config import get_settings


def write_credentials_file(path: Path, username: str, password_hash: str) -> Path:
    """Write credentials to YAML-like config and lock file permissions to user-only."""
    resolved = path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        f"username: {username}\npassword_hash: {password_hash}\n",
        encoding="utf-8",
    )
    resolved.chmod(S_IRUSR | S_IWUSR)
    return resolved


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize Ralph Dashboard credentials")
    parser.add_argument("--username", help="Dashboard username")
    parser.add_argument("--password", help="Dashboard password (avoid shell history leakage)")
    parser.add_argument("--password-confirm", help="Confirmation value for --password")
    parser.add_argument("--credentials-file", help="Override credentials file path")
    parser.add_argument("--force", action="store_true", help="Overwrite existing credentials file")
    return parser


def _prompt_username() -> str:
    username = input("Username: ").strip()
    if not username:
        raise ValueError("Username cannot be empty")
    return username


def _prompt_password() -> tuple[str, str]:
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm password: ")
    return password, password_confirm


def _resolve_inputs(args: argparse.Namespace) -> tuple[str, str]:
    username = args.username.strip() if args.username else _prompt_username()

    if args.password is not None:
        password = args.password
        password_confirm = (
            args.password_confirm if args.password_confirm is not None else args.password
        )
    else:
        password, password_confirm = _prompt_password()

    if not password:
        raise ValueError("Password cannot be empty")
    if password != password_confirm:
        raise ValueError("Password and confirmation do not match")
    return username, password


def main(argv: list[str] | None = None) -> int:
    """Run setup-user CLI workflow."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    settings = get_settings()
    credentials_file = (
        Path(args.credentials_file).expanduser().resolve()
        if args.credentials_file
        else settings.credentials_file
    )

    if credentials_file.exists() and not args.force:
        print(f"Credentials file already exists: {credentials_file}")
        print("Use --force to overwrite.")
        return 1

    try:
        username, password = _resolve_inputs(args)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    password_hash = hash_password(password)
    output_path = write_credentials_file(credentials_file, username, password_hash)
    print(f"Credentials initialized at {output_path}")
    return 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
