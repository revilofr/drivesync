from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from drivesync.cli import main
from drivesync.run import RunBatchResult, RunItemResult


class RunCliTests(unittest.TestCase):
    @patch("drivesync.cli.run_sync")
    def test_cli_run_text_success(self, mock_run_sync: object) -> None:
        mock_run_sync.return_value = RunBatchResult(
            code=0,
            status="success",
            message="Synchronisation terminee",
            items=[
                RunItemResult(
                    code=0,
                    status="success",
                    directory_id="documents",
                    local_directory=Path("/tmp/Documents"),
                    remote_directory="gdrive:DriveSync/documents",
                    message="Synchronisation terminee",
                    raw_output="",
                )
            ],
        )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "run", "documents"])

            stdout.seek(0)
            output = stdout.read().strip()

        self.assertEqual(exit_code, 0)
        self.assertEqual(output, "0|success|documents|Synchronisation terminee")
        mock_run_sync.assert_called_once_with(
            directory_id="documents",
            resync=False,
            force=False,
            trigger="manual",
            scheduler=None,
        )

    @patch("drivesync.cli.run_sync")
    def test_cli_run_json_error_no_items(self, mock_run_sync: object) -> None:
        mock_run_sync.return_value = RunBatchResult(
            code=2,
            status="error",
            message="Aucun repertoire configure",
            items=[],
        )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "run", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["code"], 2)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["items"], [])
        mock_run_sync.assert_called_once_with(
            directory_id=None,
            resync=False,
            force=False,
            trigger="manual",
            scheduler=None,
        )

    @patch("drivesync.cli.run_sync")
    def test_cli_run_json_resync(self, mock_run_sync: object) -> None:
        mock_run_sync.return_value = RunBatchResult(
            code=0,
            status="success",
            message="Synchronisation terminee",
            items=[
                RunItemResult(
                    code=0,
                    status="success",
                    directory_id="projects",
                    local_directory=Path("/tmp/Projects"),
                    remote_directory="gdrive:DriveSync/projects",
                    message="Synchronisation terminee",
                    raw_output="",
                )
            ],
        )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "run", "projects", "--resync", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["code"], 0)
        self.assertEqual(payload["items"][0]["id"], "projects")
        mock_run_sync.assert_called_once_with(
            directory_id="projects",
            resync=True,
            force=False,
            trigger="manual",
            scheduler=None,
        )

    @patch("drivesync.cli.run_sync")
    def test_cli_run_force_flag(self, mock_run_sync: object) -> None:
        mock_run_sync.return_value = RunBatchResult(
            code=0,
            status="success",
            message="Synchronisation terminee",
            items=[],
        )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "run", "documents", "--resync", "--force"])

            stdout.seek(0)
            _ = stdout.read().strip()

        self.assertEqual(exit_code, 0)
        mock_run_sync.assert_called_once_with(
            directory_id="documents",
            resync=True,
            force=True,
            trigger="manual",
            scheduler=None,
        )


if __name__ == "__main__":
    unittest.main()