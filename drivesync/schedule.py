from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

from .config import ensure_config_dir, get_schedules_file
from .directories import load_directories


VALID_SCHEDULE_FREQUENCIES = {"5minutes", "hourly", "daily", "weekly"}
VALID_SCHEDULE_DAYS = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
    "sunday": 0,
}
SCHEDULE_TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
CRON_BLOCK_START = "# BEGIN DRIVESYNC SCHEDULES"
CRON_BLOCK_END = "# END DRIVESYNC SCHEDULES"

SCHEDULE_APPLY_STATUS_CURRENT = "current"
SCHEDULE_APPLY_STATUS_PENDING_INSTALL = "pending_install"
SCHEDULE_APPLY_STATUS_PENDING_UNINSTALL = "pending_uninstall"
SCHEDULE_APPLY_STATUS_STALE = "stale"


class ScheduleConfigError(ValueError):
    """Raised when a configured schedule is invalid."""


class ScheduleInstallError(RuntimeError):
    """Raised when crontab operations fail."""


@dataclass(frozen=True)
class ScheduledSync:
    directory_id: str
    frequency: str
    at_time: str | None = None
    day: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True)
class ScheduleApplyResult:
    schedule_count: int
    crontab_content: str


def normalize_schedule_frequency(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in VALID_SCHEDULE_FREQUENCIES:
        raise ScheduleConfigError(
            f"Invalid schedule frequency: {value}. Expected one of: 5minutes, hourly, daily, weekly"
        )
    return normalized


def normalize_schedule_time(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not SCHEDULE_TIME_PATTERN.fullmatch(normalized):
        raise ScheduleConfigError(f"Invalid schedule time: {value}. Expected HH:MM")
    return normalized


def normalize_schedule_day(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in VALID_SCHEDULE_DAYS:
        raise ScheduleConfigError(
            "Invalid schedule day: "
            f"{value}. Expected one of: monday, tuesday, wednesday, thursday, friday, saturday, sunday"
        )
    return normalized


def validate_schedule(
    frequency: str,
    at_time: str | None,
    day: str | None,
) -> ScheduledSync:
    normalized_frequency = normalize_schedule_frequency(frequency)
    normalized_time = normalize_schedule_time(at_time)
    normalized_day = normalize_schedule_day(day)

    if normalized_frequency == "5minutes":
        if normalized_time is not None or normalized_day is not None:
            raise ScheduleConfigError("5minutes schedules do not accept --at or --day")
    elif normalized_frequency == "hourly":
        if normalized_time is not None or normalized_day is not None:
            raise ScheduleConfigError("Hourly schedules do not accept --at or --day")
    elif normalized_frequency == "daily":
        if normalized_time is None:
            raise ScheduleConfigError("Daily schedules require --at HH:MM")
        if normalized_day is not None:
            raise ScheduleConfigError("Daily schedules do not accept --day")
    elif normalized_frequency == "weekly":
        if normalized_time is None:
            raise ScheduleConfigError("Weekly schedules require --at HH:MM")
        if normalized_day is None:
            raise ScheduleConfigError("Weekly schedules require --day")

    return ScheduledSync(directory_id="", frequency=normalized_frequency, at_time=normalized_time, day=normalized_day)


def load_schedules() -> list[ScheduledSync]:
    schedules_file = get_schedules_file()
    if not schedules_file.exists():
        return []

    try:
        payload = json.loads(schedules_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScheduleConfigError("Invalid schedules file") from exc

    if not isinstance(payload, list):
        raise ScheduleConfigError("Invalid schedules file")

    schedules: list[ScheduledSync] = []
    seen_ids: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise ScheduleConfigError("Invalid schedules entry")
        directory_id = item.get("directory_id")
        frequency = item.get("frequency")
        at_time = item.get("at_time")
        day = item.get("day")
        if not isinstance(directory_id, str) or not isinstance(frequency, str):
            raise ScheduleConfigError("Invalid schedules entry")
        normalized = validate_schedule(frequency, at_time if isinstance(at_time, str) else None, day if isinstance(day, str) else None)
        if directory_id in seen_ids:
            raise ScheduleConfigError(f"Duplicate schedule for directory id: {directory_id}")
        schedules.append(
            ScheduledSync(
                directory_id=directory_id,
                frequency=normalized.frequency,
                at_time=normalized.at_time,
                day=normalized.day,
            )
        )
        seen_ids.add(directory_id)
    return schedules


def save_schedules(schedules: list[ScheduledSync]) -> Path:
    ensure_config_dir()
    schedules_file = get_schedules_file()
    payload = [schedule.to_dict() for schedule in sorted(schedules, key=lambda item: item.directory_id)]
    schedules_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return schedules_file


def get_schedule(directory_id: str) -> ScheduledSync:
    for schedule in load_schedules():
        if schedule.directory_id == directory_id:
            return schedule
    raise ScheduleConfigError(f"Unknown schedule for directory id: {directory_id}")


def set_schedule(
    directory_id: str,
    frequency: str,
    at_time: str | None = None,
    day: str | None = None,
) -> ScheduledSync:
    managed_directory_ids = {item.directory_id for item in load_directories()}
    if directory_id not in managed_directory_ids:
        raise ScheduleConfigError(f"Unknown directory id: {directory_id}")

    normalized = validate_schedule(frequency, at_time, day)
    schedule = ScheduledSync(
        directory_id=directory_id,
        frequency=normalized.frequency,
        at_time=normalized.at_time,
        day=normalized.day,
    )

    schedules = [item for item in load_schedules() if item.directory_id != directory_id]
    schedules.append(schedule)
    save_schedules(schedules)
    return schedule


def remove_schedule(directory_id: str) -> ScheduledSync:
    schedules = load_schedules()
    for schedule in schedules:
        if schedule.directory_id == directory_id:
            save_schedules([item for item in schedules if item.directory_id != directory_id])
            return schedule
    raise ScheduleConfigError(f"Unknown schedule for directory id: {directory_id}")


def describe_schedule(schedule: ScheduledSync) -> str:
    parts = [schedule.directory_id, schedule.frequency]
    if schedule.day is not None:
        parts.append(f"day={schedule.day}")
    if schedule.at_time is not None:
        parts.append(f"at={schedule.at_time}")
    return "  ".join(parts)


def _cron_expression(schedule: ScheduledSync) -> str:
    if schedule.frequency == "5minutes":
        return "*/5 * * * *"

    if schedule.frequency == "hourly":
        return "0 * * * *"

    assert schedule.at_time is not None
    hour, minute = schedule.at_time.split(":", 1)
    if schedule.frequency == "daily":
        return f"{int(minute)} {int(hour)} * * *"

    assert schedule.day is not None
    return f"{int(minute)} {int(hour)} * * {VALID_SCHEDULE_DAYS[schedule.day]}"


def _command_prefix() -> str:
    repo_root = Path(__file__).resolve().parents[1]
    return (
        f"cd {shlex.quote(str(repo_root))} && "
        f"{shlex.quote(str(Path(sys.executable).resolve()))} -m drivesync"
    )


def render_schedule_preview() -> str:
    schedules = load_schedules()
    if not schedules:
        return ""

    lines = [CRON_BLOCK_START, "# managed by drivesync schedule install"]
    prefix = _command_prefix()
    for schedule in sorted(schedules, key=lambda item: item.directory_id):
        command = (
            f"{prefix} sync run {shlex.quote(schedule.directory_id)} "
            "--trigger scheduled --scheduler cron >/dev/null 2>&1"
        )
        lines.append(f"{_cron_expression(schedule)} {command}")
    lines.append(CRON_BLOCK_END)
    return "\n".join(lines)


def _strip_managed_block(content: str) -> str:
    kept_lines: list[str] = []
    in_block = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line == CRON_BLOCK_START:
            in_block = True
            continue
        if line == CRON_BLOCK_END:
            in_block = False
            continue
        if not in_block:
            kept_lines.append(raw_line)
    return "\n".join(kept_lines).strip()


def _extract_managed_block(content: str) -> str:
    block_lines: list[str] = []
    in_block = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line == CRON_BLOCK_START:
            in_block = True
        if in_block:
            block_lines.append(raw_line)
        if line == CRON_BLOCK_END and in_block:
            break
    return "\n".join(block_lines).strip()


def _read_crontab() -> str:
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ScheduleInstallError("crontab command not found. Install cron.") from exc

    if result.returncode == 0:
        return result.stdout.strip()

    output = ((result.stderr or "") + "\n" + (result.stdout or "")).strip().lower()
    if "no crontab for" in output:
        return ""

    lines = [line.strip() for line in output.splitlines() if line.strip()]
    raise ScheduleInstallError(lines[-1] if lines else "Unable to read current crontab")


def _write_crontab(content: str) -> None:
    try:
        result = subprocess.run(
            ["crontab", "-"],
            input=(content + "\n") if content else "",
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ScheduleInstallError("crontab command not found. Install cron.") from exc

    if result.returncode != 0:
        output = ((result.stderr or "") + "\n" + (result.stdout or "")).strip()
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        raise ScheduleInstallError(lines[-1] if lines else "Unable to update crontab")


def install_schedules() -> ScheduleApplyResult:
    existing = _read_crontab()
    preview = render_schedule_preview()
    stripped = _strip_managed_block(existing)
    parts = [part for part in [stripped, preview] if part]
    merged = "\n\n".join(parts).strip()
    _write_crontab(merged)
    return ScheduleApplyResult(schedule_count=len(load_schedules()), crontab_content=merged)


def uninstall_schedules() -> ScheduleApplyResult:
    existing = _read_crontab()
    stripped = _strip_managed_block(existing)
    _write_crontab(stripped)
    return ScheduleApplyResult(schedule_count=0, crontab_content=stripped)


def get_schedule_apply_status() -> str:
    preview = render_schedule_preview().strip()
    try:
        existing = _read_crontab()
    except ScheduleInstallError:
        return SCHEDULE_APPLY_STATUS_PENDING_INSTALL if preview else SCHEDULE_APPLY_STATUS_CURRENT

    installed = _extract_managed_block(existing).strip()
    if installed == preview:
        return SCHEDULE_APPLY_STATUS_CURRENT
    if not installed and preview:
        return SCHEDULE_APPLY_STATUS_PENDING_INSTALL
    if installed and not preview:
        return SCHEDULE_APPLY_STATUS_PENDING_UNINSTALL
    return SCHEDULE_APPLY_STATUS_STALE
