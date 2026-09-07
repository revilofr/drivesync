from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from drivesync.config import AppConfig
from drivesync.directories import ManagedDirectory
from drivesync.run import run_sync


class RunLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.docs_dir = Path(self.temp_dir.name) / "Documents"
        self.docs_dir.mkdir()
        self.config_dir = Path(self.temp_dir.name) / "config"
        self.original_config_home = os.environ.get("DRIVESYNC_CONFIG_HOME")
        os.environ["DRIVESYNC_CONFIG_HOME"] = str(self.config_dir)

    def tearDown(self) -> None:
        if self.original_config_home is None:
            os.environ.pop("DRIVESYNC_CONFIG_HOME", None)
        else:
            os.environ["DRIVESYNC_CONFIG_HOME"] = self.original_config_home
        self.temp_dir.cleanup()

    @patch("drivesync.run.get_auth_status")
    def test_run_sync_returns_auth_error(self, mock_auth_status: object) -> None:
        class _Auth:
            code = 2
            message = "auth failed"

        mock_auth_status.return_value = _Auth()
        result = run_sync()
        self.assertEqual(result.code, 2)
        self.assertEqual(result.items, [])

    @patch("drivesync.run.load_directories", return_value=[])
    @patch("drivesync.run.load_app_config")
    @patch("drivesync.run.get_auth_status")
    def test_run_sync_no_directories(
        self,
        mock_auth_status: object,
        mock_load_config: object,
        _mock_load_directories: object,
    ) -> None:
        class _Auth:
            code = 0
            message = "ok"

        mock_auth_status.return_value = _Auth()
        mock_load_config.return_value = AppConfig(remote="gdrive", root="DriveSync")

        result = run_sync()
        self.assertEqual(result.code, 2)
        self.assertIn("Aucun repertoire", result.message)

    @patch("drivesync.run.subprocess.run")
    @patch("drivesync.run._remote_has_entries", return_value=False)
    @patch("drivesync.run._local_has_entries", return_value=True)
    @patch("drivesync.run.load_directories")
    @patch("drivesync.run.load_app_config")
    @patch("drivesync.run.get_auth_status")
    def test_run_sync_single_directory_success(
        self,
        mock_auth_status: object,
        mock_load_config: object,
        mock_load_directories: object,
        _mock_local_has_entries: object,
        _mock_remote_has_entries: object,
        mock_subprocess_run: object,
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
                directory_id="documents",
                directory=self.docs_dir,
                remote_subpath="archives/documents",
            )
        ]
        mock_subprocess_run.side_effect = [_ProcResult(), _ProcResult()]

        result = run_sync("documents")
        self.assertEqual(result.code, 0)
        self.assertEqual(result.items[0].directory_id, "documents")
        self.assertEqual(result.items[0].raw_output, "")
        mkdir_command = mock_subprocess_run.call_args_list[0].args[0]
        self.assertEqual(mkdir_command[0:2], ["rclone", "mkdir"])
        self.assertEqual(mkdir_command[2], "gdrive:DriveSync/archives/documents")

        bisync_command = mock_subprocess_run.call_args_list[1].args[0]
        self.assertEqual(bisync_command[0:2], ["rclone", "bisync"])
        self.assertEqual(bisync_command[2], str(self.docs_dir))
        self.assertEqual(bisync_command[3], "gdrive:DriveSync/archives/documents")

    @patch("drivesync.run.subprocess.run")
    @patch("drivesync.run._remote_has_entries", return_value=True)
    @patch("drivesync.run._local_has_entries", return_value=True)
    @patch("drivesync.run.load_directories")
    @patch("drivesync.run.load_app_config")
    @patch("drivesync.run.get_auth_status")
    def test_run_sync_resync_refuses_non_empty_without_force(
        self,
        mock_auth_status: object,
        mock_load_config: object,
        mock_load_directories: object,
        _mock_local_has_entries: object,
        _mock_remote_has_entries: object,
        mock_subprocess_run: object,
    ) -> None:
        class _Auth:
            code = 0
            message = "ok"

        mock_auth_status.return_value = _Auth()
        mock_load_config.return_value = AppConfig(remote="gdrive", root="DriveSync")
        mock_load_directories.return_value = [
            ManagedDirectory(
                directory_id="documents",
                directory=self.docs_dir,
                remote_subpath="archives/documents",
            )
        ]

        result = run_sync("documents", resync=True)
        self.assertEqual(result.code, 2)
        self.assertIn("Refus de lancer --resync", result.items[0].message)
        self.assertEqual(mock_subprocess_run.call_count, 0)

    @patch("drivesync.run.subprocess.run")
    @patch("drivesync.run._remote_has_entries", return_value=False)
    @patch("drivesync.run._local_has_entries", return_value=False)
    @patch("drivesync.run.load_directories")
    @patch("drivesync.run.load_app_config")
    @patch("drivesync.run.get_auth_status")
    def test_run_sync_missing_bisync_state_returns_actionable_message(
        self,
        mock_auth_status: object,
        mock_load_config: object,
        mock_load_directories: object,
        _mock_local_has_entries: object,
        _mock_remote_has_entries: object,
        mock_subprocess_run: object,
    ) -> None:
        class _Auth:
            code = 0
            message = "ok"

        class _ProcOK:
            returncode = 0
            stdout = ""
            stderr = ""

        class _ProcFail:
            returncode = 1
            stdout = ""
            stderr = "Bisync aborted. Must run --resync to recover."

        class _ProcResyncOK:
            returncode = 0
            stdout = ""
            stderr = ""

        mock_auth_status.return_value = _Auth()
        mock_load_config.return_value = AppConfig(remote="gdrive", root="DriveSync")
        mock_load_directories.return_value = [
            ManagedDirectory(
                directory_id="documents",
                directory=self.docs_dir,
                remote_subpath="archives/documents",
            )
        ]
        mock_subprocess_run.side_effect = [_ProcOK(), _ProcFail(), _ProcResyncOK()]

        result = run_sync("documents")
        self.assertEqual(result.code, 0)
        self.assertIn("auto-resync", result.items[0].message)
        self.assertIn("Must run --resync to recover.", result.items[0].raw_output)

    @patch("drivesync.run.subprocess.run")
    @patch("drivesync.run._remote_has_entries", return_value=True)
    @patch("drivesync.run._local_has_entries", return_value=True)
    @patch("drivesync.run.load_directories")
    @patch("drivesync.run.load_app_config")
    @patch("drivesync.run.get_auth_status")
    def test_run_sync_missing_bisync_state_non_empty_requires_force(
        self,
        mock_auth_status: object,
        mock_load_config: object,
        mock_load_directories: object,
        _mock_local_has_entries: object,
        _mock_remote_has_entries: object,
        mock_subprocess_run: object,
    ) -> None:
        class _Auth:
            code = 0
            message = "ok"

        class _ProcOK:
            returncode = 0
            stdout = ""
            stderr = ""

        class _ProcFail:
            returncode = 1
            stdout = ""
            stderr = "Bisync aborted. Must run --resync to recover."

        mock_auth_status.return_value = _Auth()
        mock_load_config.return_value = AppConfig(remote="gdrive", root="DriveSync")
        mock_load_directories.return_value = [
            ManagedDirectory(
                directory_id="documents",
                directory=self.docs_dir,
                remote_subpath="archives/documents",
            )
        ]
        mock_subprocess_run.side_effect = [_ProcOK(), _ProcFail()]

        result = run_sync("documents")
        self.assertEqual(result.code, 2)
        self.assertIn("--resync --force", result.items[0].message)
        self.assertIn("Must run --resync to recover.", result.items[0].raw_output)

    @patch("drivesync.run.subprocess.run")
    @patch("drivesync.run._remote_has_entries", return_value=False)
    @patch("drivesync.run._local_has_entries", return_value=True)
    @patch("drivesync.run.load_directories")
    @patch("drivesync.run.load_app_config")
    @patch("drivesync.run.get_auth_status")
    def test_run_sync_full_precision_uses_verbose_rclone(
        self,
        mock_auth_status: object,
        mock_load_config: object,
        mock_load_directories: object,
        _mock_local_has_entries: object,
        _mock_remote_has_entries: object,
        mock_subprocess_run: object,
    ) -> None:
        class _Auth:
            code = 0
            message = "ok"

        class _ProcResult:
            returncode = 0
            stdout = "verbose details"
            stderr = "INFO verbose"

        mock_auth_status.return_value = _Auth()
        mock_load_config.return_value = AppConfig(
            remote="gdrive", root="DriveSync", logs_precision="full"
        )
        mock_load_directories.return_value = [
            ManagedDirectory(
                directory_id="documents",
                directory=self.docs_dir,
                remote_subpath="archives/documents",
            )
        ]
        mock_subprocess_run.side_effect = [_ProcResult(), _ProcResult()]

        result = run_sync("documents")

        self.assertEqual(result.code, 0)
        bisync_command = mock_subprocess_run.call_args_list[1].args[0]
        self.assertEqual(bisync_command[0:3], ["rclone", "-vv", "bisync"])
        self.assertIn("verbose details", result.items[0].raw_output)


if __name__ == "__main__":
    unittest.main()