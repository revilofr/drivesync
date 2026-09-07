from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from drivesync.cli import main
from drivesync.directories import add_directory
from drivesync.sync_history import append_sync_history_entry


class SyncStatusLogsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name) / "config"
        self.docs_dir = Path(self.temp_dir.name) / "Documents"
        self.docs_dir.mkdir()
        self.original_config_home = os.environ.get("DRIVESYNC_CONFIG_HOME")
        os.environ["DRIVESYNC_CONFIG_HOME"] = str(self.config_dir)

    def tearDown(self) -> None:
        if self.original_config_home is None:
            os.environ.pop("DRIVESYNC_CONFIG_HOME", None)
        else:
            os.environ["DRIVESYNC_CONFIG_HOME"] = self.original_config_home
        self.temp_dir.cleanup()

    def test_sync_status_never_run(self) -> None:
        add_directory("docs", self.docs_dir)

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "status", "docs", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload[0]["last_status"], "never_run")

    def test_sync_status_reads_last_history(self) -> None:
        add_directory("docs", self.docs_dir)
        append_sync_history_entry(
            directory_id="docs",
            code=0,
            status="success",
            local_directory=str(self.docs_dir),
            remote_directory="gdrive:DriveSync/docs",
            message="Synchronisation terminee",
            resync=False,
            force=False,
            raw_output="bisync completed",
            trigger="manual",
            scheduler=None,
        )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "status", "docs", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload[0]["last_status"], "success")

    def test_sync_status_text_includes_last_run_timestamp(self) -> None:
        add_directory("docs", self.docs_dir)
        append_sync_history_entry(
            directory_id="docs",
            code=0,
            status="success",
            local_directory=str(self.docs_dir),
            remote_directory="gdrive:DriveSync/docs",
            message="Synchronisation terminee",
            resync=False,
            force=False,
            raw_output="bisync completed",
            trigger="manual",
            scheduler=None,
        )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "status", "docs"])

            stdout.seek(0)
            output = stdout.read().strip()

        self.assertEqual(exit_code, 0)
        self.assertRegex(output, r"^0\|success\|docs\|.+\|Synchronisation terminee$")

    def test_sync_logs_path_and_events(self) -> None:
        add_directory("docs", self.docs_dir)
        append_sync_history_entry(
            directory_id="docs",
            code=2,
            status="error",
            local_directory=str(self.docs_dir),
            remote_directory="gdrive:DriveSync/docs",
            message="test error",
            resync=False,
            force=False,
            raw_output="rclone error details",
            trigger="manual",
            scheduler=None,
        )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "logs", "docs", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["events"][0]["status"], "error")
        self.assertEqual(payload["events"][0]["raw_output"], "rclone error details")

    def test_sync_logs_raw_text_output(self) -> None:
        add_directory("docs", self.docs_dir)
        append_sync_history_entry(
            directory_id="docs",
            code=0,
            status="success",
            local_directory=str(self.docs_dir),
            remote_directory="gdrive:DriveSync/docs",
            message="Synchronisation terminee",
            resync=False,
            force=False,
            raw_output="raw bisync lines",
            trigger="manual",
            scheduler=None,
        )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "logs", "docs", "--raw"])

            stdout.seek(0)
            output = stdout.read()

        self.assertEqual(exit_code, 0)
        self.assertIn("[", output)
        self.assertIn("docs", output)
        self.assertIn("raw bisync lines", output)


if __name__ == "__main__":
    unittest.main()