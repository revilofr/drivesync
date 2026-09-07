from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from .auth import get_auth_status
from .config import load_app_config
from .directories import ManagedDirectory, load_directories
from .sync_history import append_sync_history_entry


@dataclass(frozen=True)
class RunItemResult:
    code: int
    status: str
    directory_id: str
    local_directory: Path
    remote_directory: str
    message: str
    raw_output: str


@dataclass(frozen=True)
class RunBatchResult:
    code: int
    status: str
    message: str
    items: list[RunItemResult]


def _append_history_safe(
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
    try:
        append_sync_history_entry(
            directory_id=directory_id,
            code=code,
            status=status,
            local_directory=local_directory,
            remote_directory=remote_directory,
            message=message,
            resync=resync,
            force=force,
            raw_output=raw_output,
            trigger=trigger,
            scheduler=scheduler,
        )
    except OSError:
        pass


def _append_batch_failure_history(
    *,
    directory_id: str | None,
    message: str,
    resync: bool,
    force: bool,
    trigger: str,
    scheduler: str | None,
) -> None:
    if directory_id is None:
        return

    local_directory = ""
    remote_directory = ""
    config = load_app_config()
    for managed_directory in load_directories():
        if managed_directory.directory_id != directory_id:
            continue
        local_directory = str(managed_directory.directory)
        if config.remote:
            remote_directory = _to_remote_directory(
                config.remote,
                config.root,
                managed_directory.remote_subpath,
            )
        break

    _append_history_safe(
        directory_id=directory_id,
        code=2,
        status="error",
        local_directory=local_directory,
        remote_directory=remote_directory,
        message=message,
        resync=resync,
        force=force,
        raw_output="",
        trigger=trigger,
        scheduler=scheduler,
    )


def _normalize_remote_name(remote: str) -> str:
    return remote.strip().rstrip(":")


def _to_remote_directory(remote: str, root: str, remote_subpath: str) -> str:
    return f"{_normalize_remote_name(remote)}:{root}/{remote_subpath}"


def _local_has_entries(local_directory: Path) -> bool:
    return any(local_directory.iterdir())


def _remote_has_entries(remote_directory: str) -> bool:
    result = subprocess.run(
        ["rclone", "lsf", remote_directory, "--max-depth", "1"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def _is_missing_bisync_state(output: str) -> bool:
    lowered = output.lower()
    return (
        "must run --resync to recover" in lowered
        or "cannot find prior path1 or path2 listings" in lowered
    )


def _format_bisync_error(output: str, directory_id: str) -> str:
    if _is_missing_bisync_state(output):
        return (
            f"Etat bisync absent/invalide pour '{directory_id}'. "
            f"Relancez: drivesync sync run {directory_id} --resync"
        )

    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if lines:
        return lines[-1]
    return "rclone bisync a echoue"


def _run_bisync(
    managed_directory: ManagedDirectory,
    remote: str,
    root: str,
    resync: bool,
    force: bool,
    logs_precision: str,
) -> RunItemResult:
    remote_directory = _to_remote_directory(remote, root, managed_directory.remote_subpath)

    local_non_empty = _local_has_entries(managed_directory.directory)
    remote_non_empty = _remote_has_entries(remote_directory)

    if resync and not force:
        if local_non_empty and remote_non_empty:
            return RunItemResult(
                code=2,
                status="error",
                directory_id=managed_directory.directory_id,
                local_directory=managed_directory.directory,
                remote_directory=remote_directory,
                message=(
                    "Refus de lancer --resync: local et remote contiennent deja des fichiers. "
                    "Relancez avec --force si vous confirmez."
                ),
                raw_output="",
            )

    ensure_remote_result = subprocess.run(
        ["rclone", "mkdir", remote_directory],
        capture_output=True,
        text=True,
        check=False,
    )
    if ensure_remote_result.returncode != 0:
        output = (ensure_remote_result.stderr or "").strip() or (
            ensure_remote_result.stdout or ""
        ).strip()
        error_message = output.splitlines()[-1] if output else "rclone mkdir a echoue"
        return RunItemResult(
            code=2,
            status="error",
            directory_id=managed_directory.directory_id,
            local_directory=managed_directory.directory,
            remote_directory=remote_directory,
            message=error_message,
            raw_output=output,
        )

    command = [
        "rclone",
        "bisync",
        str(managed_directory.directory),
        remote_directory,
    ]
    if logs_precision == "full":
        command.insert(1, "-vv")
    if resync:
        command.append("--resync")

    result = subprocess.run(command, capture_output=True, text=True, check=False)
    raw_output = ((result.stderr or "") + "\n" + (result.stdout or "")).strip()
    if result.returncode == 0:
        return RunItemResult(
            code=0,
            status="success",
            directory_id=managed_directory.directory_id,
            local_directory=managed_directory.directory,
            remote_directory=remote_directory,
            message="Synchronisation terminee",
            raw_output=raw_output,
        )

    output = raw_output

    # UX helper: if bisync state is missing, attempt an automatic --resync when safe.
    if not resync and _is_missing_bisync_state(output):
        if local_non_empty and remote_non_empty and not force:
            return RunItemResult(
                code=2,
                status="error",
                directory_id=managed_directory.directory_id,
                local_directory=managed_directory.directory,
                remote_directory=remote_directory,
                message=(
                    "Etat bisync absent/invalide et local/remote deja non vides. "
                    "Relancez avec: drivesync sync run "
                    f"{managed_directory.directory_id} --resync --force"
                ),
                raw_output=output,
            )

        auto_resync_result = subprocess.run(
            [
                "rclone",
                *(["-vv"] if logs_precision == "full" else []),
                "bisync",
                str(managed_directory.directory),
                remote_directory,
                "--resync",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        auto_resync_output = ((auto_resync_result.stderr or "") + "\n" + (auto_resync_result.stdout or "")).strip()
        if auto_resync_result.returncode == 0:
            return RunItemResult(
                code=0,
                status="success",
                directory_id=managed_directory.directory_id,
                local_directory=managed_directory.directory,
                remote_directory=remote_directory,
                message="Synchronisation terminee (auto-resync)",
                raw_output=(
                    output
                    if not auto_resync_output
                    else f"{output}\n\n--- auto-resync ---\n{auto_resync_output}"
                ).strip(),
            )

        output = (
            output
            if not auto_resync_output
            else f"{output}\n\n--- auto-resync ---\n{auto_resync_output}"
        ).strip()

    error_message = _format_bisync_error(output, managed_directory.directory_id)
    return RunItemResult(
        code=2,
        status="error",
        directory_id=managed_directory.directory_id,
        local_directory=managed_directory.directory,
        remote_directory=remote_directory,
        message=error_message,
        raw_output=output,
    )


def run_sync(
    directory_id: str | None = None,
    resync: bool = False,
    force: bool = False,
    trigger: str = "manual",
    scheduler: str | None = None,
) -> RunBatchResult:
    auth_status = get_auth_status()
    if auth_status.code != 0:
        _append_batch_failure_history(
            directory_id=directory_id,
            message=auth_status.message,
            resync=resync,
            force=force,
            trigger=trigger,
            scheduler=scheduler,
        )
        return RunBatchResult(
            code=2,
            status="error",
            message=auth_status.message,
            items=[],
        )

    config = load_app_config()
    if not config.remote:
        _append_batch_failure_history(
            directory_id=directory_id,
            message="Aucun remote configure dans drivesync",
            resync=resync,
            force=force,
            trigger=trigger,
            scheduler=scheduler,
        )
        return RunBatchResult(
            code=2,
            status="error",
            message="Aucun remote configure dans drivesync",
            items=[],
        )

    managed_directories = load_directories()
    if directory_id is not None:
        managed_directories = [
            managed_directory
            for managed_directory in managed_directories
            if managed_directory.directory_id == directory_id
        ]
        if not managed_directories:
            _append_batch_failure_history(
                directory_id=directory_id,
                message=f"Unknown directory id: {directory_id}",
                resync=resync,
                force=force,
                trigger=trigger,
                scheduler=scheduler,
            )
            return RunBatchResult(
                code=2,
                status="error",
                message=f"Unknown directory id: {directory_id}",
                items=[],
            )

    if not managed_directories:
        _append_batch_failure_history(
            directory_id=directory_id,
            message="Aucun repertoire configure. Utilisez 'drivesync dir add'.",
            resync=resync,
            force=force,
            trigger=trigger,
            scheduler=scheduler,
        )
        return RunBatchResult(
            code=2,
            status="error",
            message="Aucun repertoire configure. Utilisez 'drivesync dir add'.",
            items=[],
        )

    items = [
        _run_bisync(
            managed_directory=managed_directory,
            remote=config.remote,
            root=config.root,
            resync=resync,
            force=force,
            logs_precision=config.logs_precision,
        )
        for managed_directory in managed_directories
    ]

    for item in items:
        _append_history_safe(
            directory_id=item.directory_id,
            code=item.code,
            status=item.status,
            local_directory=str(item.local_directory),
            remote_directory=item.remote_directory,
            message=item.message,
            resync=resync,
            force=force,
            raw_output=item.raw_output,
            trigger=trigger,
            scheduler=scheduler,
        )

    if any(item.code != 0 for item in items):
        return RunBatchResult(
            code=2,
            status="error",
            message="Au moins une synchronisation a echoue",
            items=items,
        )

    return RunBatchResult(
        code=0,
        status="success",
        message="Synchronisation terminee",
        items=items,
    )