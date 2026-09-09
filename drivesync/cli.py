from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from .auth import get_auth_status, setup_auth
from .config import (
    AppConfig,
    clear_config_dir_override,
    get_config_dir,
    get_config_dir_source,
    get_config_file,
    get_directories_file,
    get_schedules_file,
    get_sync_history_file,
    load_app_config,
    normalize_logs_max_size_kb,
    normalize_logs_precision,
    normalize_remote_root,
    set_config_dir_override,
    save_app_config,
)
from .directories import DirectoryConfigError, add_directory, load_directories, remove_directory
from .rclone import run_preflight_check
from .run import run_sync
from .schedule import (
    ScheduleConfigError,
    ScheduleInstallError,
    ScheduledSync,
    describe_schedule,
    get_schedule_apply_status,
    get_schedule,
    install_schedules,
    load_schedules,
    remove_schedule,
    render_schedule_preview,
    SCHEDULE_APPLY_STATUS_PENDING_INSTALL,
    SCHEDULE_APPLY_STATUS_PENDING_UNINSTALL,
    SCHEDULE_APPLY_STATUS_STALE,
    set_schedule,
    uninstall_schedules,
)
from .sync_history import get_sync_history_path, load_sync_history
from .status import (
    DirectoryHealth,
    STATUS_ERROR,
    STATUS_LATE,
    STATUS_OFFLINE,
    STATUS_OK,
    STATUS_UNKNOWN,
    evaluate_directory_health,
)

DEFAULT_FOLLOW_TAIL = 10


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise ValueError("tail must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="drivesync",
        description="Pattern: drivesync <sujet> <action>",
    )
    subparsers = parser.add_subparsers(dest="command")

    status_command_parser = subparsers.add_parser(
        "status", help="Show compact or detailed synchronization status"
    )
    status_command_parser.add_argument("directory_id", nargs="?", default=None)
    status_command_parser.add_argument("--executor", action="store_true", dest="executor")
    status_command_parser.add_argument("--json", action="store_true", dest="as_json")

    dir_parser = subparsers.add_parser("dir", help="Manage synchronized directories")
    dir_subparsers = dir_parser.add_subparsers(dest="dir_command")

    add_parser = dir_subparsers.add_parser("add", help="Register a local directory")
    add_parser.add_argument("directory_id")
    add_parser.add_argument("directory")
    add_parser.add_argument(
        "--create",
        action="store_true",
        dest="create_missing",
        help="Create local directory if it does not exist",
    )
    add_parser.add_argument(
        "--remote-dir",
        dest="remote_dir",
        default=None,
        help="Remote subdirectory under configured root (default: directory id)",
    )

    remove_parser = dir_subparsers.add_parser("remove", help="Unregister a local directory")
    remove_parser.add_argument("directory_id")

    list_parser = dir_subparsers.add_parser("list", help="List managed directories")
    list_parser.add_argument("--json", action="store_true", dest="as_json")

    show_parser = dir_subparsers.add_parser("show", help="Show one managed directory")
    show_parser.add_argument("directory_id")
    show_parser.add_argument("--json", action="store_true", dest="as_json")

    sync_parser = subparsers.add_parser("sync", help="Synchronization commands")
    sync_subparsers = sync_parser.add_subparsers(dest="sync_command")

    check_parser = sync_subparsers.add_parser("check", help="Run preflight checks")
    check_parser.add_argument("--json", action="store_true", dest="as_json")

    run_parser = sync_subparsers.add_parser(
        "run",
        help=(
            "Run synchronization (auto-resync if bisync state is missing; "
            "explicit force still required for risky conflict cases)"
        ),
    )
    run_parser.add_argument("directory_id", nargs="?", default=None)
    run_parser.add_argument("--resync", action="store_true", dest="resync")
    run_parser.add_argument(
        "--force",
        action="store_true",
        dest="force",
        help="Allow risky --resync when both local and remote are non-empty",
    )
    run_parser.add_argument("--trigger", default="manual", help=argparse.SUPPRESS)
    run_parser.add_argument("--scheduler", default=None, help=argparse.SUPPRESS)
    run_parser.add_argument("--json", action="store_true", dest="as_json")

    status_parser = sync_subparsers.add_parser("status", help="Show synchronization status")
    status_parser.add_argument("directory_id", nargs="?", default=None)
    status_parser.add_argument("--executor", action="store_true", dest="executor")
    status_parser.add_argument("--json", action="store_true", dest="as_json")

    logs_parser = sync_subparsers.add_parser("logs", help="Inspect synchronization logs")
    logs_parser.add_argument("directory_id", nargs="?", default=None)
    logs_parser.add_argument("--path", action="store_true", dest="path_only")
    logs_parser.add_argument("--raw", action="store_true", dest="raw_output")
    logs_parser.add_argument("--tail", type=_positive_int, dest="tail", default=None)
    logs_parser.add_argument("--follow", "-f", action="store_true", dest="follow")
    logs_parser.add_argument("--json", action="store_true", dest="as_json")

    config_parser = subparsers.add_parser("config", help="Inspect DriveSync configuration paths")
    config_subparsers = config_parser.add_subparsers(dest="config_command")

    config_path_parser = config_subparsers.add_parser("path", help="Configuration path commands")
    config_path_subparsers = config_path_parser.add_subparsers(dest="config_path_command")

    config_logs_parser = config_subparsers.add_parser(
        "logs", help="Configure rclone log capture"
    )
    config_logs_subparsers = config_logs_parser.add_subparsers(dest="config_logs_command")

    config_logs_precision_parser = config_logs_subparsers.add_parser(
        "precision", help="Set/show rclone log precision"
    )
    config_logs_precision_subparsers = config_logs_precision_parser.add_subparsers(
        dest="config_logs_precision_command"
    )

    config_logs_precision_show_parser = config_logs_precision_subparsers.add_parser(
        "show", help="Show configured logs precision"
    )
    config_logs_precision_show_parser.add_argument("--json", action="store_true", dest="as_json")

    config_logs_precision_set_parser = config_logs_precision_subparsers.add_parser(
        "set", help="Set logs precision"
    )
    config_logs_precision_set_parser.add_argument("precision", choices=["light", "full"])
    config_logs_precision_set_parser.add_argument("--json", action="store_true", dest="as_json")

    config_logs_max_size_parser = config_logs_subparsers.add_parser(
        "max-size", help="Set/show sync history max size in KB"
    )
    config_logs_max_size_subparsers = config_logs_max_size_parser.add_subparsers(
        dest="config_logs_max_size_command"
    )

    config_logs_max_size_show_parser = config_logs_max_size_subparsers.add_parser(
        "show", help="Show configured sync history max size in KB"
    )
    config_logs_max_size_show_parser.add_argument("--json", action="store_true", dest="as_json")

    config_logs_max_size_set_parser = config_logs_max_size_subparsers.add_parser(
        "set", help="Set sync history max size in KB"
    )
    config_logs_max_size_set_parser.add_argument("size_kb", type=int)
    config_logs_max_size_set_parser.add_argument("--json", action="store_true", dest="as_json")

    config_path_show_parser = config_path_subparsers.add_parser("show", help="Show resolved config paths")
    config_path_show_parser.add_argument("--json", action="store_true", dest="as_json")

    config_path_set_parser = config_path_subparsers.add_parser("set", help="Set persistent config dir")
    config_path_set_parser.add_argument("path")
    config_path_set_parser.add_argument("--json", action="store_true", dest="as_json")

    config_path_reset_parser = config_path_subparsers.add_parser(
        "reset", help="Reset to default config dir resolution"
    )
    config_path_reset_parser.add_argument("--json", action="store_true", dest="as_json")

    config_root_parser = config_subparsers.add_parser(
        "root", help="Configure remote root directory in cloud storage"
    )
    config_root_subparsers = config_root_parser.add_subparsers(dest="config_root_command")

    config_root_show_parser = config_root_subparsers.add_parser(
        "show", help="Show configured remote root directory in cloud storage"
    )
    config_root_show_parser.add_argument("--json", action="store_true", dest="as_json")

    config_root_set_parser = config_root_subparsers.add_parser(
        "set", help="Set remote root directory in cloud storage"
    )
    config_root_set_parser.add_argument("root")
    config_root_set_parser.add_argument("--json", action="store_true", dest="as_json")

    config_root_reset_parser = config_root_subparsers.add_parser(
        "reset", help="Reset remote root directory in cloud storage to default"
    )
    config_root_reset_parser.add_argument("--json", action="store_true", dest="as_json")

    auth_parser = subparsers.add_parser("auth", help="Manage rclone authentication")
    auth_subparsers = auth_parser.add_subparsers(dest="auth_command")

    auth_status_parser = auth_subparsers.add_parser("status", help="Check rclone auth state")
    auth_status_parser.add_argument("--json", action="store_true", dest="as_json")

    auth_setup_parser = auth_subparsers.add_parser("setup", help="Configure rclone remote for DriveSync")
    auth_setup_parser.add_argument("remote", nargs="?", default=None)
    auth_setup_parser.add_argument("--json", action="store_true", dest="as_json")

    schedule_parser = subparsers.add_parser(
        "schedule",
        help="Manage local schedules and apply them to user crontab",
        description=(
            "Manage DriveSync scheduled synchronizations. "
            "Use 'set' and 'remove' to change the local schedule configuration, "
            "then run 'install' or 'uninstall' to apply those changes to the user crontab."
        ),
    )
    schedule_subparsers = schedule_parser.add_subparsers(dest="schedule_command")

    schedule_set_parser = schedule_subparsers.add_parser(
        "set",
        help="Create or update one local schedule configuration",
        description=(
            "Create or update the local DriveSync schedule configuration for one directory id. "
            "This command does not update cron by itself; run 'drivesync schedule install' afterward "
            "to apply the current configuration to the user crontab."
        ),
    )
    schedule_set_parser.add_argument("directory_id", help="Managed directory id to schedule")
    schedule_set_parser.add_argument(
        "--frequency",
        required=True,
        choices=["5minutes", "hourly", "daily", "weekly"],
        help="Execution frequency for this directory id",
    )
    schedule_set_parser.add_argument(
        "--at",
        dest="at_time",
        default=None,
        help="Execution time in HH:MM for daily or weekly schedules",
    )
    schedule_set_parser.add_argument(
        "--day",
        default=None,
        help="Execution day for weekly schedules: monday..sunday",
    )
    schedule_set_parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output the saved local schedule configuration as JSON",
    )

    schedule_show_parser = schedule_subparsers.add_parser("show", help="Show one configured schedule")
    schedule_show_parser.add_argument("directory_id")
    schedule_show_parser.add_argument("--json", action="store_true", dest="as_json")

    schedule_list_parser = schedule_subparsers.add_parser("list", help="List configured schedules")
    schedule_list_parser.add_argument("--json", action="store_true", dest="as_json")

    schedule_remove_parser = schedule_subparsers.add_parser(
        "remove",
        help="Remove one local schedule configuration",
        description=(
            "Remove one schedule from the local DriveSync configuration. "
            "This command does not update cron by itself; run 'drivesync schedule install' "
            "or 'drivesync schedule uninstall' afterward to apply the change to the user crontab."
        ),
    )
    schedule_remove_parser.add_argument("directory_id", help="Managed directory id to unschedule")
    schedule_remove_parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output the removed local schedule configuration as JSON",
    )

    schedule_preview_parser = schedule_subparsers.add_parser(
        "preview",
        help="Preview the cron block DriveSync would install",
        description=(
            "Show the exact cron block that DriveSync would write into the user crontab "
            "when running 'drivesync schedule install'."
        ),
    )
    schedule_preview_parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output the generated cron block as JSON",
    )

    schedule_install_parser = schedule_subparsers.add_parser(
        "install",
        help="Apply current local schedule configuration to user crontab",
        description=(
            "Write the current local DriveSync schedule configuration into the user crontab. "
            "The managed DriveSync cron block is replaced with the current preview."
        ),
    )
    schedule_install_parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output the resulting crontab content as JSON",
    )

    schedule_uninstall_parser = schedule_subparsers.add_parser(
        "uninstall",
        help="Remove the managed DriveSync block from user crontab",
        description=(
            "Remove only the managed DriveSync cron block from the user crontab. "
            "The local DriveSync schedule configuration is kept unchanged."
        ),
    )
    schedule_uninstall_parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output the resulting crontab content as JSON",
    )

    return parser


def _print_directories(as_json: bool) -> int:
    managed_directories = load_directories()
    if as_json:
        payload = [
            {
                "id": managed_directory.directory_id,
                "directory": str(managed_directory.directory),
                "remote_directory": managed_directory.remote_subpath,
            }
            for managed_directory in managed_directories
        ]
        print(json.dumps(payload, indent=2))
        return 0

    if not managed_directories:
        return 0

    width = max(len(item.directory_id) for item in managed_directories)
    for managed_directory in managed_directories:
        print(
            f"{managed_directory.directory_id.ljust(width)}  "
            f"{managed_directory.directory} -> {managed_directory.remote_subpath}"
        )
    return 0


def _print_directory(directory_id: str, as_json: bool) -> int:
    for managed_directory in load_directories():
        if managed_directory.directory_id != directory_id:
            continue

        if as_json:
            payload = {
                "id": managed_directory.directory_id,
                "directory": str(managed_directory.directory),
                "remote_directory": managed_directory.remote_subpath,
            }
            print(json.dumps(payload, indent=2))
            return 0

        print(
            f"{managed_directory.directory_id}  "
            f"{managed_directory.directory} -> {managed_directory.remote_subpath}"
        )
        return 0

    print(f"Unknown directory id: {directory_id}", file=sys.stderr)
    return 2


def _print_check(as_json: bool) -> int:
    result = run_preflight_check()
    auth_status = get_auth_status()

    if result.code != 0:
        if as_json:
            payload = {
                "code": result.code,
                "status": result.status,
                "message": result.message,
                "rclone_version": result.rclone_version,
                "auth": {
                    "code": auth_status.code,
                    "status": auth_status.status,
                    "remote": auth_status.remote,
                    "message": auth_status.message,
                },
            }
            print(json.dumps(payload, indent=2))
        else:
            print(f"{result.code}|{result.status}|{result.message}")
        return 2

    if auth_status.code != 0:
        if as_json:
            payload = {
                "code": auth_status.code,
                "status": "error",
                "message": auth_status.message,
                "rclone_version": result.rclone_version,
                "auth": {
                    "code": auth_status.code,
                    "status": auth_status.status,
                    "remote": auth_status.remote,
                    "message": auth_status.message,
                },
            }
            print(json.dumps(payload, indent=2))
        else:
            print(f"2|error|{auth_status.message}")
        return 2

    if as_json:
        payload = {
            "code": 0,
            "status": "success",
            "message": "Configuration valide et remote accessible",
            "rclone_version": result.rclone_version,
            "auth": {
                "code": auth_status.code,
                "status": auth_status.status,
                "remote": auth_status.remote,
                "message": auth_status.message,
            },
        }
        print(json.dumps(payload, indent=2))
        return 0

    print("0|success|Configuration valide et remote accessible")
    return 0


def _print_auth_status(as_json: bool) -> int:
    result = get_auth_status()
    if as_json:
        payload = {
            "code": result.code,
            "status": result.status,
            "remote": result.remote,
            "message": result.message,
        }
        print(json.dumps(payload, indent=2))
        return 0 if result.code == 0 else 2

    remote = result.remote or "-"
    print(f"{result.code}|{result.status}|{remote}|{result.message}")
    return 0 if result.code == 0 else 2


def _print_auth_setup(remote: str | None, as_json: bool) -> int:
    result = setup_auth(remote)
    if as_json:
        payload = {
            "code": result.code,
            "status": result.status,
            "remote": result.remote,
            "message": result.message,
        }
        print(json.dumps(payload, indent=2))
        return 0 if result.code == 0 else 2

    selected_remote = result.remote or "-"
    print(f"{result.code}|{result.status}|{selected_remote}|{result.message}")
    return 0 if result.code == 0 else 2


def _schedule_payload(schedule: ScheduledSync) -> dict[str, str | None]:
    return {
        "id": schedule.directory_id,
        "frequency": schedule.frequency,
        "at": schedule.at_time,
        "day": schedule.day,
    }


def _print_run(
    directory_id: str | None,
    resync: bool,
    force: bool,
    trigger: str,
    scheduler: str | None,
    as_json: bool,
) -> int:
    result = run_sync(
        directory_id=directory_id,
        resync=resync,
        force=force,
        trigger=trigger,
        scheduler=scheduler,
    )
    if as_json:
        payload = {
            "code": result.code,
            "status": result.status,
            "message": result.message,
            "trigger": trigger,
            "scheduler": scheduler,
            "items": [
                {
                    "code": item.code,
                    "status": item.status,
                    "id": item.directory_id,
                    "local_directory": str(item.local_directory),
                    "remote_directory": item.remote_directory,
                    "message": item.message,
                }
                for item in result.items
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0 if result.code == 0 else 2

    if not result.items:
        print(f"{result.code}|{result.status}|{result.message}")
        return 0 if result.code == 0 else 2

    for item in result.items:
        print(f"{item.code}|{item.status}|{item.directory_id}|{item.message}")
    return 0 if result.code == 0 else 2


def _print_config_path(as_json: bool, set_path: str | None, reset_path: bool) -> int:
    if set_path is not None:
        set_config_dir_override(set_path)
    elif reset_path:
        clear_config_dir_override()

    config_dir = get_config_dir()
    config_file = get_config_file()
    directories_file = get_directories_file()
    sync_history_file = get_sync_history_file()
    schedules_file = get_schedules_file()
    source = get_config_dir_source()

    if as_json:
        payload = {
            "config_dir": str(config_dir),
            "config_file": str(config_file),
            "directories_file": str(directories_file),
            "sync_history_file": str(sync_history_file),
            "schedules_file": str(schedules_file),
            "source": source,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"source={source}")
    print(f"config_dir={config_dir}")
    print(f"config_file={config_file}")
    print(f"directories_file={directories_file}")
    print(f"sync_history_file={sync_history_file}")
    print(f"schedules_file={schedules_file}")
    return 0


def _print_not_implemented(command: str, as_json: bool) -> int:
    message = f"{command} not implemented yet"
    if as_json:
        print(json.dumps({"code": 2, "status": "not_implemented", "message": message}, indent=2))
    else:
        print(f"2|not_implemented|{message}")
    return 2


def _print_logs_precision(as_json: bool, precision: str | None = None) -> int:
    config = load_app_config()
    resolved_precision = config.logs_precision

    if precision is not None:
        resolved_precision = normalize_logs_precision(precision)
        save_app_config(
            AppConfig(
                remote=config.remote,
                root=config.root,
                logs_precision=resolved_precision,
                logs_max_size_kb=config.logs_max_size_kb,
            )
        )

    if as_json:
        print(json.dumps({"precision": resolved_precision}, indent=2))
        return 0

    print(f"precision={resolved_precision}")
    return 0


def _print_logs_max_size(as_json: bool, size_kb: int | None = None) -> int:
    config = load_app_config()
    resolved_size_kb = config.logs_max_size_kb

    if size_kb is not None:
        resolved_size_kb = normalize_logs_max_size_kb(size_kb)
        save_app_config(
            AppConfig(
                remote=config.remote,
                root=config.root,
                logs_precision=config.logs_precision,
                logs_max_size_kb=resolved_size_kb,
            )
        )

    if as_json:
        print(json.dumps({"max_size_kb": resolved_size_kb}, indent=2))
        return 0

    print(f"max_size_kb={resolved_size_kb}")
    return 0


def _print_schedule_list(as_json: bool) -> int:
    schedules = load_schedules()
    if as_json:
        print(json.dumps([_schedule_payload(item) for item in schedules], indent=2))
        return 0

    if not schedules:
        print("0|empty|Aucune planification configuree")
        return 0

    for schedule in schedules:
        print(describe_schedule(schedule))
    return 0


def _print_schedule_show(directory_id: str, as_json: bool) -> int:
    schedule = get_schedule(directory_id)
    if as_json:
        print(json.dumps(_schedule_payload(schedule), indent=2))
        return 0

    print(describe_schedule(schedule))
    return 0


def _print_schedule_set(
    directory_id: str,
    frequency: str,
    at_time: str | None,
    day: str | None,
    as_json: bool,
) -> int:
    schedule = set_schedule(directory_id, frequency=frequency, at_time=at_time, day=day)
    apply_status = get_schedule_apply_status()
    if as_json:
        print(json.dumps(_schedule_payload(schedule), indent=2))
        _print_schedule_apply_hint(apply_status)
        return 0

    print(describe_schedule(schedule))
    _print_schedule_apply_hint(apply_status)
    return 0


def _print_schedule_remove(directory_id: str, as_json: bool) -> int:
    schedule = remove_schedule(directory_id)
    apply_status = get_schedule_apply_status()
    if as_json:
        print(json.dumps(_schedule_payload(schedule), indent=2))
        _print_schedule_apply_hint(apply_status)
        return 0

    print(f"Removed schedule for {schedule.directory_id}")
    _print_schedule_apply_hint(apply_status)
    return 0


def _print_schedule_apply_hint(apply_status: str) -> None:
    if apply_status == SCHEDULE_APPLY_STATUS_PENDING_INSTALL:
        print(
            "Schedule updated locally but not installed in cron. Run 'drivesync schedule install'.",
            file=sys.stderr,
        )
        return

    if apply_status == SCHEDULE_APPLY_STATUS_PENDING_UNINSTALL:
        print(
            "No schedules remain locally, but cron still has a DriveSync block. Run 'drivesync schedule uninstall'.",
            file=sys.stderr,
        )
        return

    if apply_status == SCHEDULE_APPLY_STATUS_STALE:
        print(
            "Cron still contains an older DriveSync schedule block. Run 'drivesync schedule install' to apply the current configuration.",
            file=sys.stderr,
        )


def _print_schedule_preview(as_json: bool) -> int:
    preview = render_schedule_preview()
    schedules = load_schedules()
    if as_json:
        print(json.dumps({"count": len(schedules), "crontab": preview}, indent=2))
        return 0

    if not preview:
        print("0|empty|Aucune planification configuree")
        return 0

    print(preview)
    return 0


def _print_schedule_install(as_json: bool) -> int:
    result = install_schedules()
    if as_json:
        print(json.dumps({"count": result.schedule_count, "crontab": result.crontab_content}, indent=2))
        return 0

    print(f"Applied {result.schedule_count} schedule(s) to user crontab")
    return 0


def _print_schedule_uninstall(as_json: bool) -> int:
    result = uninstall_schedules()
    if as_json:
        print(json.dumps({"count": result.schedule_count, "crontab": result.crontab_content}, indent=2))
        return 0

    print("Removed DriveSync schedules from user crontab")
    return 0


def _print_config_root(as_json: bool, root: str | None = None, reset_root: bool = False) -> int:
    config = load_app_config()
    resolved_root = config.root

    if root is not None:
        resolved_root = normalize_remote_root(root)
        save_app_config(
            AppConfig(
                remote=config.remote,
                root=resolved_root,
                logs_precision=config.logs_precision,
                logs_max_size_kb=config.logs_max_size_kb,
            )
        )
    elif reset_root:
        resolved_root = normalize_remote_root(None)
        save_app_config(
            AppConfig(
                remote=config.remote,
                root=resolved_root,
                logs_precision=config.logs_precision,
                logs_max_size_kb=config.logs_max_size_kb,
            )
        )

    if as_json:
        print(json.dumps({"root": resolved_root}, indent=2))
        return 0

    print(f"root={resolved_root}")
    return 0


def _should_prompt_for_directory_creation(path: Path) -> bool:
    if path.exists():
        return False
    return sys.stdin.isatty()


def _confirm_create_directory(path: Path) -> bool:
    answer = input(
        f"Local directory does not exist on this machine: {path} (not on remote drive). "
        "Create it now? [y/N]: "
    ).strip().lower()
    return answer in {"y", "yes"}


def _print_sync_status(directory_id: str | None, as_json: bool) -> int:
    managed_directories = load_directories()
    if directory_id is not None:
        managed_directories = [item for item in managed_directories if item.directory_id == directory_id]
        if not managed_directories:
            print(f"Unknown directory id: {directory_id}", file=sys.stderr)
            return 2

    history = load_sync_history()
    last_by_id: dict[str, dict[str, object]] = {}
    for entry in history:
        entry_id = entry.get("directory_id")
        if isinstance(entry_id, str):
            last_by_id[entry_id] = entry

    if as_json:
        payload = []
        for item in managed_directories:
            last = last_by_id.get(item.directory_id)
            if last is None:
                payload.append(
                    {
                        "id": item.directory_id,
                        "directory": str(item.directory),
                        "remote_directory": item.remote_subpath,
                        "last_run": None,
                        "last_code": None,
                        "last_status": "never_run",
                        "last_message": "Aucune synchronisation enregistree",
                    }
                )
                continue

            payload.append(
                {
                    "id": item.directory_id,
                    "directory": str(item.directory),
                    "remote_directory": item.remote_subpath,
                    "last_run": last.get("timestamp"),
                    "last_code": last.get("code"),
                    "last_status": last.get("status"),
                    "last_message": last.get("message"),
                }
            )
        print(json.dumps(payload, indent=2))
        return 0

    if not managed_directories:
        print("0|empty|Aucun repertoire configure")
        return 0

    for item in managed_directories:
        last = last_by_id.get(item.directory_id)
        if last is None:
            print(f"1|never_run|{item.directory_id}|-|Aucune synchronisation enregistree")
            continue
        print(
            f"{last.get('code')}|{last.get('status')}|{item.directory_id}|{last.get('timestamp')}|"
            f"{last.get('message')}"
        )
    return 0


def _health_statuses(directory_id: str | None) -> list[DirectoryHealth] | None:
    managed_directories = load_directories()
    if directory_id is not None:
        managed_directories = [item for item in managed_directories if item.directory_id == directory_id]
        if not managed_directories:
            print(f"Unknown directory id: {directory_id}", file=sys.stderr)
            return None

    schedules = {schedule.directory_id: schedule for schedule in load_schedules()}
    history = load_sync_history()
    offline = bool(managed_directories) and get_auth_status().code != 0
    return [
        evaluate_directory_health(item, schedules.get(item.directory_id), history, offline=offline)
        for item in managed_directories
    ]


def _global_health_state(statuses: list[DirectoryHealth]) -> str:
    state_names = {status.state for status in statuses}
    if STATUS_ERROR in state_names:
        return STATUS_ERROR
    if STATUS_OFFLINE in state_names:
        return STATUS_OFFLINE
    if STATUS_LATE in state_names or STATUS_UNKNOWN in state_names:
        return STATUS_LATE
    return STATUS_OK


def _print_health_status(
    directory_id: str | None,
    as_json: bool,
    executor: bool,
) -> int:
    statuses = _health_statuses(directory_id)
    if statuses is None:
        return 2

    global_state = _global_health_state(statuses)
    if executor:
        symbol = {
            STATUS_OK: "🟢",
            STATUS_ERROR: "🔴",
            STATUS_LATE: "🟠",
            STATUS_OFFLINE: "⚪",
        }[global_state]
        print(f" ☁️ {symbol} ")
        return 0

    if as_json:
        print(json.dumps({
            "status": global_state,
            "executor": f"☁️ {'🟢' if global_state == STATUS_OK else '🔴' if global_state == STATUS_ERROR else '⚪' if global_state == STATUS_OFFLINE else '🟠'}",
            "directories": [status.to_dict() for status in statuses],
        }, indent=2))
        return 0

    labels = {
        STATUS_OK: "OK",
        STATUS_ERROR: "ERREUR",
        STATUS_LATE: "EN RETARD",
        STATUS_UNKNOWN: "INCONNU",
        STATUS_OFFLINE: "HORS LIGNE",
    }
    print(f"Statut global : {labels[global_state]}")
    for status in statuses:
        print(f"- {status.directory_id}: {labels[status.state]} ({status.reason})")
    return 0


def _print_sync_logs(
    directory_id: str | None,
    path_only: bool,
    raw_output: bool,
    tail: int | None,
    follow: bool,
    as_json: bool,
) -> int:
    if follow and tail is None:
        tail = DEFAULT_FOLLOW_TAIL
    if follow and as_json:
        raise ValueError("--follow is not supported with --json")
    if follow and path_only:
        raise ValueError("--follow cannot be used with --path")

    managed_directories = load_directories()
    if directory_id is not None and not any(item.directory_id == directory_id for item in managed_directories):
        print(f"Unknown directory id: {directory_id}", file=sys.stderr)
        return 2

    history_path = get_sync_history_path()
    history = load_sync_history()
    if directory_id is not None:
        history = [entry for entry in history if entry.get("directory_id") == directory_id]
    full_history = history
    if tail is not None:
        history = history[-tail:]

    if as_json:
        payload: dict[str, object] = {
            "path": str(history_path),
            "count": len(history),
        }
        if not path_only:
            payload["events"] = history
        print(json.dumps(payload, indent=2))
        return 0

    if path_only:
        print(history_path)
        return 0

    if raw_output:
        logs_precision = load_app_config().logs_precision

        def _print_no_raw_message() -> None:
            print(
                "0|empty|Aucun log brut capture "
                f"(precision actuelle: {logs_precision}; utilisez 'drivesync config logs precision set full')."
            )

        if not history:
            if not follow:
                _print_no_raw_message()
                return 0

        printed_any = False
        for entry in reversed(history):
            timestamp = entry.get("timestamp")
            entry_id = entry.get("directory_id")
            output = str(entry.get("raw_output") or "").strip()
            if not output:
                continue
            printed_any = True
            print(f"[{timestamp}] {entry_id}")
            print(output)
        if not follow and not printed_any:
            _print_no_raw_message()
            return 0
        if not follow:
            return 0

        known_entries = {
            json.dumps(entry, sort_keys=True, ensure_ascii=True) for entry in full_history
        }

        if not printed_any:
            _print_no_raw_message()

        try:
            while True:
                current_history = load_sync_history()
                if directory_id is not None:
                    current_history = [
                        entry for entry in current_history if entry.get("directory_id") == directory_id
                    ]

                for entry in current_history:
                    key = json.dumps(entry, sort_keys=True, ensure_ascii=True)
                    if key in known_entries:
                        continue
                    known_entries.add(key)
                    timestamp = entry.get("timestamp")
                    entry_id = entry.get("directory_id")
                    output = str(entry.get("raw_output") or "").strip()
                    if not output:
                        continue
                    print(f"[{timestamp}] {entry_id}")
                    print(output)

                time.sleep(1)
        except KeyboardInterrupt:
            return 0

    if not history:
        if not follow:
            print("0|empty|Aucun log de synchronisation")
            return 0

    for entry in reversed(history):
        timestamp = entry.get("timestamp")
        entry_id = entry.get("directory_id")
        status = entry.get("status")
        message = entry.get("message")
        print(f"{timestamp}|{entry_id}|{status}|{message}")
    if not follow:
        return 0

    known_entries = {
        json.dumps(entry, sort_keys=True, ensure_ascii=True) for entry in full_history
    }

    try:
        while True:
            current_history = load_sync_history()
            if directory_id is not None:
                current_history = [entry for entry in current_history if entry.get("directory_id") == directory_id]

            for entry in current_history:
                key = json.dumps(entry, sort_keys=True, ensure_ascii=True)
                if key in known_entries:
                    continue
                known_entries.add(key)
                timestamp = entry.get("timestamp")
                entry_id = entry.get("directory_id")
                status = entry.get("status")
                message = entry.get("message")
                print(f"{timestamp}|{entry_id}|{status}|{message}")

            time.sleep(1)
    except KeyboardInterrupt:
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "status":
            return _print_health_status(args.directory_id, args.as_json, args.executor)

        if args.command == "sync":
            if args.sync_command == "check":
                return _print_check(args.as_json)

            if args.sync_command == "run":
                return _print_run(
                    args.directory_id,
                    args.resync,
                    args.force,
                    args.trigger,
                    args.scheduler,
                    args.as_json,
                )

            if args.sync_command == "status":
                if args.executor:
                    return _print_health_status(args.directory_id, False, True)
                return _print_sync_status(args.directory_id, args.as_json)

            if args.sync_command == "logs":
                return _print_sync_logs(
                    args.directory_id,
                    args.path_only,
                    args.raw_output,
                    args.tail,
                    args.follow,
                    args.as_json,
                )

            sync_parser = next(
                action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
            )
            sync_parser.choices["sync"].print_help()
            return 1

        if args.command == "config":
            if args.config_command == "path":
                if args.config_path_command == "show":
                    return _print_config_path(args.as_json, None, False)
                if args.config_path_command == "set":
                    return _print_config_path(args.as_json, args.path, False)
                if args.config_path_command == "reset":
                    return _print_config_path(args.as_json, None, True)

                config_parser = next(
                    action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
                )
                config_parser.choices["config"].print_help()
                return 1

            if args.config_command == "root":
                if args.config_root_command == "show":
                    return _print_config_root(args.as_json)
                if args.config_root_command == "set":
                    return _print_config_root(args.as_json, args.root, False)
                if args.config_root_command == "reset":
                    return _print_config_root(args.as_json, None, True)

                config_parser = next(
                    action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
                )
                config_parser.choices["config"].print_help()
                return 1

            if args.config_command == "logs":
                if args.config_logs_command == "precision":
                    if args.config_logs_precision_command == "show":
                        return _print_logs_precision(args.as_json)
                    if args.config_logs_precision_command == "set":
                        return _print_logs_precision(args.as_json, args.precision)

                if args.config_logs_command == "max-size":
                    if args.config_logs_max_size_command == "show":
                        return _print_logs_max_size(args.as_json)
                    if args.config_logs_max_size_command == "set":
                        return _print_logs_max_size(args.as_json, args.size_kb)

                config_parser = next(
                    action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
                )
                config_parser.choices["config"].print_help()
                return 1

            config_parser = next(
                action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
            )
            config_parser.choices["config"].print_help()
            return 1

        if args.command == "auth":
            if args.auth_command == "status":
                return _print_auth_status(args.as_json)
            if args.auth_command == "setup":
                return _print_auth_setup(args.remote, args.as_json)

            auth_parser = next(
                action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
            )
            auth_parser.choices["auth"].print_help()
            return 1

        if args.command == "schedule":
            if args.schedule_command == "set":
                return _print_schedule_set(
                    args.directory_id,
                    args.frequency,
                    args.at_time,
                    args.day,
                    args.as_json,
                )
            if args.schedule_command == "show":
                return _print_schedule_show(args.directory_id, args.as_json)
            if args.schedule_command == "list":
                return _print_schedule_list(args.as_json)
            if args.schedule_command == "remove":
                return _print_schedule_remove(args.directory_id, args.as_json)
            if args.schedule_command == "preview":
                return _print_schedule_preview(args.as_json)
            if args.schedule_command == "install":
                return _print_schedule_install(args.as_json)
            if args.schedule_command == "uninstall":
                return _print_schedule_uninstall(args.as_json)

            schedule_parser = next(
                action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
            )
            schedule_parser.choices["schedule"].print_help()
            return 1

        if args.command != "dir":
            parser.print_help()
            return 1

        if args.dir_command == "add":
            requested_path = Path(args.directory).expanduser()
            if args.create_missing and not requested_path.exists():
                requested_path.mkdir(parents=True, exist_ok=True)
            elif _should_prompt_for_directory_creation(requested_path):
                if _confirm_create_directory(requested_path):
                    requested_path.mkdir(parents=True, exist_ok=True)
                else:
                    print(
                        f"Local directory does not exist on this machine: {args.directory} "
                        "(not on remote drive)",
                        file=sys.stderr,
                    )
                    return 2

            managed_directory = add_directory(args.directory_id, args.directory, args.remote_dir)
            print(
                f"{managed_directory.directory_id} -> {managed_directory.directory} "
                f"(remote: {managed_directory.remote_subpath})"
            )
            return 0

        if args.dir_command == "remove":
            managed_directory = remove_directory(args.directory_id)
            print(f"Removed {managed_directory.directory_id} -> {managed_directory.directory}")
            return 0

        if args.dir_command == "list":
            return _print_directories(args.as_json)

        if args.dir_command == "show":
            return _print_directory(args.directory_id, args.as_json)

        dir_parser = next(
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        )
        dir_parser.choices["dir"].print_help()
        return 1
    except (DirectoryConfigError, ScheduleConfigError, ScheduleInstallError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())