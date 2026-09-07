from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import patch

from drivesync.cli import main
from drivesync.auth import AuthSetupResult, AuthStatusResult
from drivesync.rclone import CheckResult, parse_rclone_version, run_preflight_check


class RcloneVersionTests(unittest.TestCase):
    def test_parse_rclone_version_release(self) -> None:
        output = "rclone v1.75.1\n- os/type: linux"
        self.assertEqual(parse_rclone_version(output), (1, 75, 1))

    def test_parse_rclone_version_dev(self) -> None:
        output = "rclone v1.60.1-DEV\n- os/type: linux"
        self.assertEqual(parse_rclone_version(output), (1, 60, 1))

    def test_parse_rclone_version_invalid(self) -> None:
        self.assertIsNone(parse_rclone_version("not a version"))

    @patch("drivesync.rclone.shutil.which", return_value=None)
    def test_preflight_missing_rclone(self, _mock_which: object) -> None:
        result = run_preflight_check()
        self.assertEqual(result.code, 2)
        self.assertEqual(result.status, "error")


class CheckCliTests(unittest.TestCase):
    @patch("drivesync.cli.get_auth_status")
    @patch("drivesync.cli.run_preflight_check")
    def test_cli_check_text(self, mock_preflight: object, mock_auth_status: object) -> None:
        mock_preflight.return_value = CheckResult(
            code=0,
            status="success",
            message="ok",
            rclone_version="1.75.1",
        )
        mock_auth_status.return_value = AuthStatusResult(
            code=0,
            status="authenticated",
            remote="gdrive",
            message="Google Drive accessible",
        )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "check"])

            stdout.seek(0)
            output = stdout.read().strip()

        self.assertEqual(exit_code, 0)
        self.assertEqual(output, "0|success|Configuration valide et remote accessible")

    @patch("drivesync.cli.get_auth_status")
    @patch("drivesync.cli.run_preflight_check")
    def test_cli_check_json_error(self, mock_preflight: object, mock_auth_status: object) -> None:
        mock_preflight.return_value = CheckResult(
            code=2,
            status="error",
            message="old version",
            rclone_version="1.60.1",
        )
        mock_auth_status.return_value = AuthStatusResult(
            code=2,
            status="auth_error",
            remote="gdrive",
            message="auth failed",
        )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "check", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["code"], 2)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["rclone_version"], "1.60.1")

    @patch("drivesync.cli.get_auth_status")
    def test_cli_auth_status_text(self, mock_auth_status: object) -> None:
        mock_auth_status.return_value = AuthStatusResult(
            code=0,
            status="authenticated",
            remote="gdrive",
            message="Google Drive accessible",
        )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["auth", "status"])

            stdout.seek(0)
            output = stdout.read().strip()

        self.assertEqual(exit_code, 0)
        self.assertEqual(output, "0|authenticated|gdrive|Google Drive accessible")

    @patch("drivesync.cli.setup_auth")
    def test_cli_auth_setup_text(self, mock_setup_auth: object) -> None:
        mock_setup_auth.return_value = AuthSetupResult(
            code=0,
            status="configured",
            remote="gdrive",
            message="Remote configure pour DriveSync: gdrive",
        )

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["auth", "setup"])

            stdout.seek(0)
            output = stdout.read().strip()

        self.assertEqual(exit_code, 0)
        self.assertEqual(output, "0|configured|gdrive|Remote configure pour DriveSync: gdrive")


if __name__ == "__main__":
    unittest.main()