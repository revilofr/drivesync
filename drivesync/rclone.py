from __future__ import annotations

from dataclasses import dataclass
import re
import shutil
import subprocess


MIN_RCLONE_VERSION = (1, 66, 0)
RECOMMENDED_RCLONE_VERSION = (1, 71, 0)


@dataclass(frozen=True)
class CheckResult:
    code: int
    status: str
    message: str
    rclone_version: str | None = None


def _format_version(version: tuple[int, int, int]) -> str:
    return f"{version[0]}.{version[1]}.{version[2]}"


def parse_rclone_version(version_output: str) -> tuple[int, int, int] | None:
    match = re.search(r"rclone v(\d+)\.(\d+)\.(\d+)", version_output)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def run_preflight_check() -> CheckResult:
    if shutil.which("rclone") is None:
        return CheckResult(
            code=2,
            status="error",
            message="rclone n'est pas installe",
            rclone_version=None,
        )

    command_result = subprocess.run(
        ["rclone", "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    combined_output = (command_result.stdout or "") + "\n" + (command_result.stderr or "")

    if command_result.returncode != 0:
        return CheckResult(
            code=2,
            status="error",
            message="Impossible de lire la version rclone",
            rclone_version=None,
        )

    parsed_version = parse_rclone_version(combined_output)
    if parsed_version is None:
        return CheckResult(
            code=2,
            status="error",
            message="Version rclone non lisible",
            rclone_version=None,
        )

    current_version = _format_version(parsed_version)
    minimum_version = _format_version(MIN_RCLONE_VERSION)
    recommended_version = _format_version(RECOMMENDED_RCLONE_VERSION)

    if parsed_version < MIN_RCLONE_VERSION:
        return CheckResult(
            code=2,
            status="error",
            message=(
                f"rclone {current_version} est trop ancien; minimum requis: {minimum_version}"
            ),
            rclone_version=current_version,
        )

    if parsed_version < RECOMMENDED_RCLONE_VERSION:
        return CheckResult(
            code=0,
            status="success",
            message=(
                f"rclone {current_version} OK (minimum atteint) mais version recommandee: "
                f">= {recommended_version}"
            ),
            rclone_version=current_version,
        )

    return CheckResult(
        code=0,
        status="success",
        message=f"rclone {current_version} OK",
        rclone_version=current_version,
    )