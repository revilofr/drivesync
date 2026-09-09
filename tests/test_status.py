from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from drivesync.cli import main
from drivesync.directories import ManagedDirectory
from drivesync.schedule import ScheduledSync
from drivesync.status import (
    STATUS_ERROR,
    STATUS_LATE,
    STATUS_OFFLINE,
    STATUS_OK,
    evaluate_directory_health,
)


class StatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = ManagedDirectory("docs", Path("/tmp/Documents"), "docs")
        self.schedule = ScheduledSync("docs", "hourly")
        self.now = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)

    def _entry(self, timestamp: datetime, status: str = "success", code: int = 0) -> dict[str, object]:
        return {
            "timestamp": timestamp.isoformat(),
            "directory_id": "docs",
            "status": status,
            "code": code,
            "message": status,
        }

    def test_recent_success_is_ok(self) -> None:
        result = evaluate_directory_health(
            self.directory,
            self.schedule,
            [self._entry(self.now - timedelta(minutes=90))],
            now=self.now,
        )
        self.assertEqual(result.state, STATUS_OK)

    def test_failed_last_attempt_is_error(self) -> None:
        result = evaluate_directory_health(
            self.directory,
            self.schedule,
            [self._entry(self.now - timedelta(minutes=10), "error", 2)],
            now=self.now,
        )
        self.assertEqual(result.state, STATUS_ERROR)

    def test_old_success_is_late_after_two_intervals(self) -> None:
        result = evaluate_directory_health(
            self.directory,
            self.schedule,
            [self._entry(self.now - timedelta(hours=2, minutes=1))],
            now=self.now,
        )
        self.assertEqual(result.state, STATUS_LATE)

    def test_offline_is_distinct_from_late(self) -> None:
        result = evaluate_directory_health(
            self.directory,
            self.schedule,
            [self._entry(self.now - timedelta(minutes=10))],
            now=self.now,
            offline=True,
        )
        self.assertEqual(result.state, STATUS_OFFLINE)

    def test_executor_offline_output_is_compact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            original_config_home = os.environ.get("DRIVESYNC_CONFIG_HOME")
            os.environ["DRIVESYNC_CONFIG_HOME"] = temp_dir
            try:
                from drivesync.directories import add_directory

                add_directory("docs", temp_dir)
                with tempfile.TemporaryFile(mode="w+") as stdout:
                    with patch("drivesync.cli.get_auth_status", return_value=SimpleNamespace(code=2)):
                        with redirect_stdout(stdout):
                            exit_code = main(["status", "--executor"])
                    stdout.seek(0)
                    output = stdout.read()
            finally:
                if original_config_home is None:
                    os.environ.pop("DRIVESYNC_CONFIG_HOME", None)
                else:
                    os.environ["DRIVESYNC_CONFIG_HOME"] = original_config_home

        self.assertEqual(exit_code, 0)
        self.assertEqual(output, " ☁️ ⚪ \n")

    def test_json_contains_interval_and_last_success(self) -> None:
        with patch("drivesync.cli.get_auth_status", return_value=SimpleNamespace(code=2)):
            with patch("drivesync.cli.load_directories", return_value=[self.directory]):
                with patch("drivesync.cli.load_schedules", return_value=[self.schedule]):
                    with patch("drivesync.cli.load_sync_history", return_value=[]):
                        with tempfile.TemporaryFile(mode="w+") as stdout:
                            with redirect_stdout(stdout):
                                exit_code = main(["status", "--json"])
                            stdout.seek(0)
                            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], STATUS_OFFLINE)
        self.assertEqual(payload["directories"][0]["interval_seconds"], 3600)
        self.assertIsNone(payload["directories"][0]["last_success"])
