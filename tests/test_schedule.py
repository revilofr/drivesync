from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from drivesync.cli import main
from drivesync.config import AppConfig
from drivesync.directories import ManagedDirectory, add_directory
from drivesync.run import run_sync
from drivesync.schedule import install_schedules, set_schedule, uninstall_schedules


class ScheduleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name) / "config"
        self.docs_dir = Path(self.temp_dir.name) / "Documents"
        self.projects_dir = Path(self.temp_dir.name) / "Projects"
        self.docs_dir.mkdir()
        self.projects_dir.mkdir()
        self.original_config_home = os.environ.get("DRIVESYNC_CONFIG_HOME")
        os.environ["DRIVESYNC_CONFIG_HOME"] = str(self.config_dir)
        add_directory("docs", self.docs_dir)
        add_directory("projects", self.projects_dir)

    def tearDown(self) -> None:
        if self.original_config_home is None:
            os.environ.pop("DRIVESYNC_CONFIG_HOME", None)
        else:
            os.environ["DRIVESYNC_CONFIG_HOME"] = self.original_config_home
        self.temp_dir.cleanup()

    def test_schedule_set_and_show_json(self) -> None:
        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main([
                    "schedule",
                    "set",
                    "docs",
                    "--frequency",
                    "daily",
                    "--at",
                    "22:30",
                    "--json",
                ])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["id"], "docs")
        self.assertEqual(payload["frequency"], "daily")
        self.assertEqual(payload["at"], "22:30")
        self.assertIsNone(payload["day"])

    def test_schedule_set_five_minutes_and_preview(self) -> None:
        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main([
                    "schedule",
                    "set",
                    "docs",
                    "--frequency",
                    "5minutes",
                    "--json",
                ])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["frequency"], "5minutes")

        with tempfile.TemporaryFile(mode="w+") as preview_stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(preview_stdout):
                preview_exit_code = main(["schedule", "preview"])

            preview_stdout.seek(0)
            preview_output = preview_stdout.read()

        self.assertEqual(preview_exit_code, 0)
        self.assertIn("*/5 * * * *", preview_output)

    def test_schedule_set_requires_at_for_daily(self) -> None:
        with tempfile.TemporaryFile(mode="w+") as stderr:
            from contextlib import redirect_stderr

            with redirect_stderr(stderr):
                exit_code = main(["schedule", "set", "docs", "--frequency", "daily"])

            stderr.seek(0)
            output = stderr.read()

        self.assertEqual(exit_code, 2)
        self.assertIn("Daily schedules require --at HH:MM", output)

    def test_schedule_preview_renders_cron_block(self) -> None:
        set_schedule("docs", frequency="weekly", at_time="03:15", day="sunday")

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["schedule", "preview"])

            stdout.seek(0)
            output = stdout.read()

        self.assertEqual(exit_code, 0)
        self.assertIn("# BEGIN DRIVESYNC SCHEDULES", output)
        self.assertIn("15 3 * * 0", output)
        self.assertIn("sync run docs --trigger scheduled --scheduler cron", output)

    @patch("drivesync.schedule.subprocess.run")
    def test_schedule_install_merges_user_crontab(self, mock_subprocess_run: object) -> None:
        class _ListResult:
            returncode = 0
            stdout = "MAILTO=me@example.com\n"
            stderr = ""

        class _WriteResult:
            returncode = 0
            stdout = ""
            stderr = ""

        set_schedule("docs", frequency="hourly")
        mock_subprocess_run.side_effect = [_ListResult(), _WriteResult()]

        result = install_schedules()

        self.assertEqual(result.schedule_count, 1)
        write_kwargs = mock_subprocess_run.call_args_list[1].kwargs
        self.assertIn("MAILTO=me@example.com", write_kwargs["input"])
        self.assertIn("# BEGIN DRIVESYNC SCHEDULES", write_kwargs["input"])
        self.assertIn("0 * * * *", write_kwargs["input"])

    @patch("drivesync.schedule.subprocess.run")
    def test_schedule_uninstall_removes_managed_block(self, mock_subprocess_run: object) -> None:
        class _ListResult:
            returncode = 0
            stdout = (
                "MAILTO=me@example.com\n"
                "# BEGIN DRIVESYNC SCHEDULES\n"
                "0 * * * * command\n"
                "# END DRIVESYNC SCHEDULES\n"
            )
            stderr = ""

        class _WriteResult:
            returncode = 0
            stdout = ""
            stderr = ""

        mock_subprocess_run.side_effect = [_ListResult(), _WriteResult()]

        result = uninstall_schedules()

        self.assertEqual(result.schedule_count, 0)
        write_kwargs = mock_subprocess_run.call_args_list[1].kwargs
        self.assertEqual(write_kwargs["input"], "MAILTO=me@example.com\n")

    @patch("drivesync.run.append_sync_history_entry")
    @patch("drivesync.run.subprocess.run")
    @patch("drivesync.run._remote_has_entries", return_value=False)
    @patch("drivesync.run._local_has_entries", return_value=True)
    @patch("drivesync.run.load_directories")
    @patch("drivesync.run.load_app_config")
    @patch("drivesync.run.get_auth_status")
    def test_scheduled_run_is_logged_with_trigger(
        self,
        mock_auth_status: object,
        mock_load_config: object,
        mock_load_directories: object,
        _mock_local_has_entries: object,
        _mock_remote_has_entries: object,
        mock_subprocess_run: object,
        mock_append_history_entry: object,
    ) -> None:
        class _Auth:
            code = 0
            message = "ok"

        class _ProcResult:
            returncode = 0
            stdout = ""
            stderr = ""

        mock_auth_status.return_value = _Auth()
        mock_load_config.return_value = AppConfig(remote="gdrive", root="DriveSync")
        mock_load_directories.return_value = [
            ManagedDirectory(
                directory_id="docs",
                directory=self.docs_dir,
                remote_subpath="docs",
            )
        ]
        mock_subprocess_run.side_effect = [_ProcResult(), _ProcResult()]

        result = run_sync(directory_id="docs", trigger="scheduled", scheduler="cron")

        self.assertEqual(result.code, 0)
        self.assertEqual(mock_append_history_entry.call_count, 1)
        self.assertEqual(mock_append_history_entry.call_args.kwargs["trigger"], "scheduled")
        self.assertEqual(mock_append_history_entry.call_args.kwargs["scheduler"], "cron")


if __name__ == "__main__":
    unittest.main()
