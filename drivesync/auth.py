from __future__ import annotations

from dataclasses import dataclass
import subprocess

from .config import AppConfig, load_app_config, save_app_config
from .rclone import run_preflight_check


@dataclass(frozen=True)
class AuthStatusResult:
    code: int
    status: str
    remote: str | None
    message: str


@dataclass(frozen=True)
class AuthSetupResult:
    code: int
    status: str
    remote: str | None
    message: str


def _normalize_remote_name(remote: str) -> str:
    return remote.strip().rstrip(":")


def _list_rclone_remotes() -> set[str]:
    result = subprocess.run(
        ["rclone", "listremotes"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return set()

    remotes: set[str] = set()
    for line in result.stdout.splitlines():
        remote = line.strip().rstrip(":")
        if remote:
            remotes.add(remote)
    return remotes


def _check_remote_access(remote: str) -> bool:
    result = subprocess.run(
        ["rclone", "lsd", f"{remote}:"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def get_auth_status() -> AuthStatusResult:
    preflight = run_preflight_check()
    if preflight.code != 0:
        return AuthStatusResult(
            code=2,
            status="auth_error",
            remote=None,
            message=preflight.message,
        )

    config = load_app_config()
    if not config.remote:
        return AuthStatusResult(
            code=2,
            status="auth_error",
            remote=None,
            message="Aucun remote configure dans drivesync",
        )

    configured_remote = _normalize_remote_name(config.remote)
    remotes = _list_rclone_remotes()
    if configured_remote not in remotes:
        return AuthStatusResult(
            code=2,
            status="auth_error",
            remote=config.remote,
            message=f"Remote rclone introuvable: {configured_remote}",
        )

    if not _check_remote_access(configured_remote):
        return AuthStatusResult(
            code=2,
            status="auth_error",
            remote=config.remote,
            message=f"Impossible d'acceder au remote: {configured_remote}",
        )

    return AuthStatusResult(
        code=0,
        status="authenticated",
        remote=configured_remote,
        message="Google Drive accessible",
    )


def setup_auth(remote: str | None = None) -> AuthSetupResult:
    preflight = run_preflight_check()
    if preflight.code != 0:
        return AuthSetupResult(
            code=2,
            status="auth_error",
            remote=None,
            message=preflight.message,
        )

    remotes = _list_rclone_remotes()
    if not remotes:
        return AuthSetupResult(
            code=2,
            status="auth_error",
            remote=None,
            message="Aucun remote rclone detecte. Lancez 'rclone config' d'abord.",
        )

    selected_remote = _normalize_remote_name(remote) if remote else None
    config = load_app_config()

    if selected_remote:
        if selected_remote not in remotes:
            available = ", ".join(sorted(remotes))
            return AuthSetupResult(
                code=2,
                status="auth_error",
                remote=selected_remote,
                message=(
                    f"Remote introuvable: {selected_remote}. Remotes disponibles: {available}"
                ),
            )
    elif config.remote and _normalize_remote_name(config.remote) in remotes:
        selected_remote = _normalize_remote_name(config.remote)
    elif len(remotes) == 1:
        selected_remote = next(iter(remotes))
    elif "gdrive" in remotes:
        selected_remote = "gdrive"
    else:
        available = ", ".join(sorted(remotes))
        return AuthSetupResult(
            code=2,
            status="auth_error",
            remote=None,
            message=(
                "Plusieurs remotes detectes. Precisez-en un: "
                "drivesync auth setup <remote>. "
                f"Disponibles: {available}"
            ),
        )

    if not _check_remote_access(selected_remote):
        return AuthSetupResult(
            code=2,
            status="auth_error",
            remote=selected_remote,
            message=f"Impossible d'acceder au remote: {selected_remote}",
        )

    save_app_config(
        AppConfig(
            remote=selected_remote,
            root=config.root,
            logs_precision=config.logs_precision,
        )
    )
    return AuthSetupResult(
        code=0,
        status="configured",
        remote=selected_remote,
        message=f"Remote configure pour DriveSync: {selected_remote}",
    )