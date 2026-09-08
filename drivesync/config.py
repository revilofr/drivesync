from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
import os


APP_NAME = "drivesync"
DEFAULT_REMOTE_ROOT = "DriveSync"
DEFAULT_LOGS_PRECISION = "light"
DEFAULT_LOGS_MAX_SIZE_KB = 10
VALID_LOGS_PRECISIONS = {"light", "full"}
CONFIG_PATH_OVERRIDE_FILE = "config_path"


@dataclass(frozen=True)
class AppConfig:
    remote: str | None = None
    root: str = DEFAULT_REMOTE_ROOT
    logs_precision: str = DEFAULT_LOGS_PRECISION
    logs_max_size_kb: int = DEFAULT_LOGS_MAX_SIZE_KB


def normalize_remote_root(value: str | None) -> str:
    normalized = (value or DEFAULT_REMOTE_ROOT).strip().strip("/")
    if not normalized:
        raise ValueError("Remote root must not be empty")
    if ":" in normalized:
        raise ValueError("Remote root must not contain ':'")
    return normalized


def normalize_logs_precision(value: str | None) -> str:
    normalized = (value or DEFAULT_LOGS_PRECISION).strip().lower()
    if normalized not in VALID_LOGS_PRECISIONS:
        raise ValueError(
            f"Invalid logs precision: {value}. Expected one of: light, full"
        )
    return normalized


def normalize_logs_max_size_kb(value: int | str | None) -> int:
    if value is None:
        return DEFAULT_LOGS_MAX_SIZE_KB

    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid logs max size: {value}. Expected a positive integer in KB"
        ) from exc

    if normalized <= 0:
        raise ValueError(
            f"Invalid logs max size: {value}. Expected a positive integer in KB"
        )
    return normalized


def _bootstrap_config_dir() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home).expanduser().resolve() / APP_NAME
    return Path.home() / ".config" / APP_NAME


def _get_config_dir_override() -> Path | None:
    override_file = _bootstrap_config_dir() / CONFIG_PATH_OVERRIDE_FILE
    if not override_file.exists():
        return None

    raw_value = override_file.read_text(encoding="utf-8").strip()
    if not raw_value:
        return None
    return Path(raw_value).expanduser().resolve()


def get_config_dir_source() -> str:
    if os.environ.get("DRIVESYNC_CONFIG_HOME"):
        return "env"
    if _get_config_dir_override() is not None:
        return "config"
    if os.environ.get("XDG_CONFIG_HOME"):
        return "xdg"
    return "default"


def get_config_dir() -> Path:
    base_dir = os.environ.get("DRIVESYNC_CONFIG_HOME")
    if base_dir:
        return Path(base_dir).expanduser().resolve()

    override_dir = _get_config_dir_override()
    if override_dir is not None:
        return override_dir

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home).expanduser().resolve() / APP_NAME

    return Path.home() / ".config" / APP_NAME


def get_config_file() -> Path:
    return get_config_dir() / "config.ini"


def get_directories_file() -> Path:
    return get_config_dir() / "directories.conf"


def get_sync_history_file() -> Path:
    return get_config_dir() / "sync-history.jsonl"


def get_schedules_file() -> Path:
    return get_config_dir() / "schedules.json"


def ensure_config_dir() -> Path:
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def set_config_dir_override(path: str | Path) -> Path:
    override_dir = Path(path).expanduser().resolve()
    bootstrap_dir = _bootstrap_config_dir()
    bootstrap_dir.mkdir(parents=True, exist_ok=True)
    override_file = bootstrap_dir / CONFIG_PATH_OVERRIDE_FILE
    with override_file.open("w", encoding="utf-8") as handle:
        handle.write(str(override_dir) + "\n")
    return override_dir


def clear_config_dir_override() -> None:
    override_file = _bootstrap_config_dir() / CONFIG_PATH_OVERRIDE_FILE
    if override_file.exists():
        override_file.unlink()


def load_app_config() -> AppConfig:
    parser = ConfigParser()
    config_file = get_config_file()
    if not config_file.exists():
        return AppConfig()

    parser.read(config_file)
    if not parser.has_section("drive"):
        return AppConfig()

    remote = parser.get("drive", "remote", fallback=None)
    root = normalize_remote_root(parser.get("drive", "root", fallback=DEFAULT_REMOTE_ROOT))
    logs_precision = normalize_logs_precision(
        parser.get("logs", "precision", fallback=DEFAULT_LOGS_PRECISION)
    )
    logs_max_size_kb = normalize_logs_max_size_kb(
        parser.get("logs", "max_size_kb", fallback=str(DEFAULT_LOGS_MAX_SIZE_KB))
    )
    return AppConfig(
        remote=remote,
        root=root,
        logs_precision=logs_precision,
        logs_max_size_kb=logs_max_size_kb,
    )


def save_app_config(config: AppConfig) -> Path:
    ensure_config_dir()
    parser = ConfigParser()
    parser["drive"] = {"root": normalize_remote_root(config.root)}
    if config.remote:
        parser["drive"]["remote"] = config.remote
    parser["logs"] = {
        "precision": normalize_logs_precision(config.logs_precision),
        "max_size_kb": str(normalize_logs_max_size_kb(config.logs_max_size_kb)),
    }

    config_file = get_config_file()
    with config_file.open("w", encoding="utf-8") as handle:
        parser.write(handle)
    return config_file