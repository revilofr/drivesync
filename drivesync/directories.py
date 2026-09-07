from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .config import ensure_config_dir, get_directories_file


DIRECTORY_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class DirectoryConfigError(ValueError):
    """Raised when a managed directory configuration is invalid."""


@dataclass(frozen=True)
class ManagedDirectory:
    directory_id: str
    directory: Path
    remote_subpath: str


def _normalize_directory_path(directory: str | Path) -> Path:
    path = Path(directory).expanduser()
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise DirectoryConfigError(f"Local directory does not exist: {directory}") from exc

    if not resolved.is_dir():
        raise DirectoryConfigError(f"Path is not a directory: {resolved}")
    return resolved


def validate_directory_id(directory_id: str) -> None:
    if not DIRECTORY_ID_PATTERN.fullmatch(directory_id):
        raise DirectoryConfigError(
            "Directory id must contain only letters, digits, '-' or '_'"
        )


def _normalize_remote_subpath(remote_subpath: str) -> str:
    value = remote_subpath.strip().strip("/")
    if not value:
        raise DirectoryConfigError("Remote directory must not be empty")
    if ":" in value:
        raise DirectoryConfigError("Remote directory must not contain ':'")
    return value


def load_directories() -> list[ManagedDirectory]:
    directories_file = get_directories_file()
    if not directories_file.exists():
        return []

    managed_directories: list[ManagedDirectory] = []
    seen_ids: set[str] = set()
    seen_remote_subpaths: set[str] = set()

    with directories_file.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise DirectoryConfigError(
                    f"Invalid directories entry at line {line_number}: {raw_line.rstrip()}"
                )

            directory_id, raw_value = line.split("=", 1)
            directory_id = directory_id.strip()
            raw_value = raw_value.strip()
            validate_directory_id(directory_id)
            if directory_id in seen_ids:
                raise DirectoryConfigError(f"Duplicate directory id in config: {directory_id}")

            if "|" in raw_value:
                raw_directory, raw_remote_subpath = raw_value.split("|", 1)
                raw_directory = raw_directory.strip()
                remote_subpath = _normalize_remote_subpath(raw_remote_subpath)
            else:
                # Backward compatibility for old format: id=/local/path
                raw_directory = raw_value
                remote_subpath = directory_id

            if remote_subpath in seen_remote_subpaths:
                raise DirectoryConfigError(
                    f"Duplicate remote directory in config: {remote_subpath}"
                )

            managed_directories.append(
                ManagedDirectory(
                    directory_id=directory_id,
                    directory=Path(raw_directory),
                    remote_subpath=remote_subpath,
                )
            )
            seen_ids.add(directory_id)
            seen_remote_subpaths.add(remote_subpath)

    return managed_directories


def save_directories(managed_directories: list[ManagedDirectory]) -> Path:
    ensure_config_dir()
    directories_file = get_directories_file()
    lines = [
        (
            f"{managed_directory.directory_id}={managed_directory.directory}"
            f"|{managed_directory.remote_subpath}"
        )
        for managed_directory in sorted(managed_directories, key=lambda item: item.directory_id)
    ]
    content = "\n".join(lines)
    if content:
        content += "\n"

    with directories_file.open("w", encoding="utf-8") as handle:
        handle.write(content)

    return directories_file


def add_directory(
    directory_id: str,
    directory: str | Path,
    remote_subpath: str | None = None,
) -> ManagedDirectory:
    validate_directory_id(directory_id)
    resolved_directory = _normalize_directory_path(directory)
    normalized_remote_subpath = _normalize_remote_subpath(remote_subpath or directory_id)
    managed_directories = load_directories()

    if any(item.directory_id == directory_id for item in managed_directories):
        raise DirectoryConfigError(f"Directory id already exists: {directory_id}")

    if any(item.remote_subpath == normalized_remote_subpath for item in managed_directories):
        raise DirectoryConfigError(
            f"Remote directory already used: {normalized_remote_subpath}"
        )

    managed_directory = ManagedDirectory(
        directory_id=directory_id,
        directory=resolved_directory,
        remote_subpath=normalized_remote_subpath,
    )
    managed_directories.append(managed_directory)
    save_directories(managed_directories)
    return managed_directory


def remove_directory(directory_id: str) -> ManagedDirectory:
    managed_directories = load_directories()
    for managed_directory in managed_directories:
        if managed_directory.directory_id == directory_id:
            updated_directories = [
                item for item in managed_directories if item.directory_id != directory_id
            ]
            save_directories(updated_directories)
            return managed_directory

    raise DirectoryConfigError(f"Unknown directory id: {directory_id}")