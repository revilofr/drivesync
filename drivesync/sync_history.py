from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from .config import ensure_config_dir, get_sync_history_file


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

    history_file = get_sync_history_file()
    with history_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=True) + "\n")


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