from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from .directories import ManagedDirectory
from .schedule import ScheduledSync


STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_LATE = "late"
STATUS_UNKNOWN = "unknown"
STATUS_OFFLINE = "offline"
STATUS_TOLERANCE_MULTIPLIER = 2

SCHEDULE_INTERVALS = {
    "5minutes": timedelta(minutes=5),
    "hourly": timedelta(hours=1),
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
}


@dataclass(frozen=True)
class DirectoryHealth:
    directory_id: str
    directory: str
    remote_directory: str
    state: str
    interval_seconds: int | None
    last_attempt: dict[str, Any] | None
    last_success: dict[str, Any] | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _timestamp(entry: dict[str, Any]) -> datetime | None:
    value = entry.get("timestamp")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def _latest(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    dated_entries = [(entry, _timestamp(entry)) for entry in entries]
    valid_entries = [(entry, timestamp) for entry, timestamp in dated_entries if timestamp is not None]
    if valid_entries:
        return max(valid_entries, key=lambda item: item[1])[0]
    return entries[-1] if entries else None


def evaluate_directory_health(
    directory: ManagedDirectory,
    schedule: ScheduledSync | None,
    history: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    offline: bool = False,
) -> DirectoryHealth:
    current_time = now or datetime.now(timezone.utc)
    entries = [entry for entry in history if entry.get("directory_id") == directory.directory_id]
    last_attempt = _latest(entries)
    successes = [entry for entry in entries if entry.get("status") == "success" or entry.get("code") == 0]
    last_success = _latest(successes)
    interval = SCHEDULE_INTERVALS.get(schedule.frequency) if schedule is not None else None
    interval_seconds = int(interval.total_seconds()) if interval is not None else None

    if last_attempt is not None and last_attempt.get("status") != "success" and last_attempt.get("code") != 0:
        state = STATUS_ERROR
        reason = "last_attempt_failed"
    elif offline:
        state = STATUS_OFFLINE
        reason = "remote_unavailable"
    elif interval is None:
        state = STATUS_UNKNOWN
        reason = "no_schedule"
    elif last_success is None or _timestamp(last_success) is None:
        state = STATUS_LATE
        reason = "never_succeeded"
    elif current_time - _timestamp(last_success) > interval * STATUS_TOLERANCE_MULTIPLIER:
        state = STATUS_LATE
        reason = "last_success_too_old"
    else:
        state = STATUS_OK
        reason = "healthy"

    return DirectoryHealth(
        directory_id=directory.directory_id,
        directory=str(directory.directory),
        remote_directory=directory.remote_subpath,
        state=state,
        interval_seconds=interval_seconds,
        last_attempt=last_attempt,
        last_success=last_success,
        reason=reason,
    )