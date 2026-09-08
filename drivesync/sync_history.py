from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from .config import ensure_config_dir, get_sync_history_file, load_app_config


def _list_history_archives(history_file: Path) -> list[Path]:
    pattern = f"{history_file.stem}-*{history_file.suffix}"
    return sorted(history_file.parent.glob(pattern))


def _cleanup_older_archives(history_file: Path, keep: Path) -> None:
    for archive in _list_history_archives(history_file):
        if archive == keep:
            continue
        try:
            archive.unlink()
        except OSError:
            continue


def _rotate_history_if_needed(history_file: Path, max_size_bytes: int, next_line_bytes: int) -> None:
    if not history_file.exists():
        return

    current_size = history_file.stat().st_size
    if current_size + next_line_bytes <= max_size_bytes:
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    archive_file = history_file.with_name(
        f"{history_file.stem}-{timestamp}{history_file.suffix}"
    )
    history_file.replace(archive_file)
    _cleanup_older_archives(history_file, archive_file)


def append_sync_history_entry(
    *,
    directory_id: str,
    code: int,
    status: str,
    local_directory: str,
    remote_directory: str,
    message: str,
    resync: bool,
    force: bool,
    raw_output: str,
    trigger: str,
    scheduler: str | None,
) -> None:
    ensure_config_dir()
    config = load_app_config()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "directory_id": directory_id,
        "code": code,
        "status": status,
        "local_directory": local_directory,
        "remote_directory": remote_directory,
        "message": message,
        "resync": resync,
        "force": force,
        "raw_output": raw_output,
        "trigger": trigger,
        "scheduler": scheduler,
    }

    line = json.dumps(entry, ensure_ascii=True) + "\n"
    history_file = get_sync_history_file()
    max_size_bytes = config.logs_max_size_kb * 1024
    _rotate_history_if_needed(history_file, max_size_bytes, len(line.encode("utf-8")))

    with history_file.open("a", encoding="utf-8") as handle:
        handle.write(line)


def load_sync_history() -> list[dict[str, object]]:
    history_file = get_sync_history_file()
    if not history_file.exists():
        return []

    entries: list[dict[str, object]] = []
    with history_file.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                entries.append(data)
    return entries


def get_sync_history_path() -> Path:
    return get_sync_history_file()