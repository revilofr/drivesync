from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from drivesync.cli import main
from drivesync.directories import add_directory
from drivesync.sync_history import append_sync_history_entry, get_sync_history_path


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

    def test_sync_logs_tail_json(self) -> None:
        add_directory("docs", self.docs_dir)
        for idx in range(1, 4):
            append_sync_history_entry(
                directory_id="docs",
                code=0,
                status="success",
                local_directory=str(self.docs_dir),
                remote_directory="gdrive:DriveSync/docs",
                message=f"run{idx}",
                resync=False,
                force=False,
                raw_output=f"raw {idx}",
                trigger="manual",
                scheduler=None,
            )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "logs", "docs", "--tail", "2", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["events"][0]["message"], "run2")
        self.assertEqual(payload["events"][1]["message"], "run3")

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

    def test_sync_logs_tail_raw_text_output(self) -> None:
        add_directory("docs", self.docs_dir)
        append_sync_history_entry(
            directory_id="docs",
            code=0,
            status="success",
            local_directory=str(self.docs_dir),
            remote_directory="gdrive:DriveSync/docs",
            message="run1",
            resync=False,
            force=False,
            raw_output="raw-one",
            trigger="manual",
            scheduler=None,
        )
        append_sync_history_entry(
            directory_id="docs",
            code=0,
            status="success",
            local_directory=str(self.docs_dir),
            remote_directory="gdrive:DriveSync/docs",
            message="run2",
            resync=False,
            force=False,
            raw_output="raw-two",
            trigger="manual",
            scheduler=None,
        )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "logs", "docs", "--raw", "--tail", "1"])

            stdout.seek(0)
            output = stdout.read()

        self.assertEqual(exit_code, 0)
        self.assertIn("raw-two", output)
        self.assertNotIn("raw-one", output)

    def test_sync_history_rotates_and_prunes_older_archives(self) -> None:
        add_directory("docs", self.docs_dir)
        set_exit_code = main(["config", "logs", "max-size", "set", "1"])
        self.assertEqual(set_exit_code, 0)

        append_sync_history_entry(
            directory_id="docs",
            code=0,
            status="success",
            local_directory=str(self.docs_dir),
            remote_directory="gdrive:DriveSync/docs",
            message="run1",
            resync=False,
            force=False,
            raw_output="x" * 700,
            trigger="manual",
            scheduler=None,
        )

        history_path = get_sync_history_path()
        first_archives = sorted(history_path.parent.glob("sync-history-*.jsonl"))
        self.assertEqual(len(first_archives), 0)

        append_sync_history_entry(
            directory_id="docs",
            code=0,
            status="success",
            local_directory=str(self.docs_dir),
            remote_directory="gdrive:DriveSync/docs",
            message="run2",
            resync=False,
            force=False,
            raw_output="x" * 700,
            trigger="manual",
            scheduler=None,
        )

        second_archives = sorted(history_path.parent.glob("sync-history-*.jsonl"))
        self.assertEqual(len(second_archives), 1)
        with history_path.open("r", encoding="utf-8") as handle:
            current_after_second = [json.loads(line) for line in handle if line.strip()]
        self.assertEqual(len(current_after_second), 1)
        self.assertEqual(current_after_second[0]["message"], "run2")

        append_sync_history_entry(
            directory_id="docs",
            code=0,
            status="success",
            local_directory=str(self.docs_dir),
            remote_directory="gdrive:DriveSync/docs",
            message="run3",
            resync=False,
            force=False,
            raw_output="x" * 700,
            trigger="manual",
            scheduler=None,
        )

        third_archives = sorted(history_path.parent.glob("sync-history-*.jsonl"))
        self.assertEqual(len(third_archives), 1)
        with third_archives[0].open("r", encoding="utf-8") as handle:
            latest_archive = [json.loads(line) for line in handle if line.strip()]
        with history_path.open("r", encoding="utf-8") as handle:
            current_after_third = [json.loads(line) for line in handle if line.strip()]

        self.assertEqual(len(latest_archive), 1)
        self.assertEqual(latest_archive[0]["message"], "run2")
        self.assertEqual(len(current_after_third), 1)
        self.assertEqual(current_after_third[0]["message"], "run3")


if __name__ == "__main__":
    unittest.main()