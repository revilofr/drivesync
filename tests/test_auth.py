from __future__ import annotations

import unittest
from unittest.mock import patch

from drivesync.auth import get_auth_status, setup_auth
from drivesync.config import AppConfig
from drivesync.rclone import CheckResult


class AuthStatusTests(unittest.TestCase):
    @patch("drivesync.auth.run_preflight_check")
    def test_auth_status_preflight_error(self, mock_preflight: object) -> None:
        mock_preflight.return_value = CheckResult(
            code=2,
            status="error",
            message="rclone missing",
            rclone_version=None,
        )

        result = get_auth_status()
        self.assertEqual(result.code, 2)
        self.assertEqual(result.status, "auth_error")

    @patch("drivesync.auth.load_app_config")
    @patch("drivesync.auth.run_preflight_check")
    def test_auth_status_no_remote(self, mock_preflight: object, mock_load_config: object) -> None:
        mock_preflight.return_value = CheckResult(
            code=0,
            status="success",
            message="ok",
            rclone_version="1.75.1",
        )
        mock_load_config.return_value = AppConfig(remote=None)

        result = get_auth_status()
        self.assertEqual(result.code, 2)
        self.assertIn("Aucun remote", result.message)

    @patch("drivesync.auth._check_remote_access", return_value=True)
    @patch("drivesync.auth._list_rclone_remotes", return_value={"gdrive"})
    @patch("drivesync.auth.load_app_config")
    @patch("drivesync.auth.run_preflight_check")
    def test_auth_status_success(
        self,
        mock_preflight: object,
        mock_load_config: object,
        _mock_list_remotes: object,
        _mock_access: object,
    ) -> None:
        mock_preflight.return_value = CheckResult(
            code=0,
            status="success",
            message="ok",
            rclone_version="1.75.1",
        )
        mock_load_config.return_value = AppConfig(remote="gdrive")

        result = get_auth_status()
        self.assertEqual(result.code, 0)
        self.assertEqual(result.status, "authenticated")
        self.assertEqual(result.remote, "gdrive")


class AuthSetupTests(unittest.TestCase):
    @patch("drivesync.auth.run_preflight_check")
    def test_setup_auth_preflight_error(self, mock_preflight: object) -> None:
        mock_preflight.return_value = CheckResult(
            code=2,
            status="error",
            message="rclone missing",
            rclone_version=None,
        )

        result = setup_auth()
        self.assertEqual(result.code, 2)
        self.assertEqual(result.status, "auth_error")

    @patch("drivesync.auth._list_rclone_remotes", return_value=set())
    @patch("drivesync.auth.run_preflight_check")
    def test_setup_auth_no_remote_detected(
        self,
        mock_preflight: object,
        _mock_list_remotes: object,
    ) -> None:
        mock_preflight.return_value = CheckResult(
            code=0,
            status="success",
            message="ok",
            rclone_version="1.75.1",
        )

        result = setup_auth()
        self.assertEqual(result.code, 2)
        self.assertIn("Aucun remote", result.message)

    @patch("drivesync.auth.save_app_config")
    @patch("drivesync.auth._check_remote_access", return_value=True)
    @patch("drivesync.auth._list_rclone_remotes", return_value={"gdrive", "work"})
    @patch("drivesync.auth.load_app_config")
    @patch("drivesync.auth.run_preflight_check")
    def test_setup_auth_with_explicit_remote_success(
        self,
        mock_preflight: object,
        mock_load_config: object,
        _mock_list_remotes: object,
        _mock_access: object,
        mock_save: object,
    ) -> None:
        mock_preflight.return_value = CheckResult(
            code=0,
            status="success",
            message="ok",
            rclone_version="1.75.1",
        )
        mock_load_config.return_value = AppConfig(remote=None, root="DriveSync")

        result = setup_auth("work")
        self.assertEqual(result.code, 0)
        self.assertEqual(result.status, "configured")
        self.assertEqual(result.remote, "work")
        self.assertTrue(mock_save.called)

    @patch("drivesync.auth.save_app_config")
    @patch("drivesync.auth._check_remote_access", return_value=True)
    @patch("drivesync.auth._list_rclone_remotes", return_value={"gdrive-personal"})
    @patch("drivesync.auth.load_app_config")
    @patch("drivesync.auth.run_preflight_check")
    def test_setup_auth_accepts_remote_with_trailing_colon(
        self,
        mock_preflight: object,
        mock_load_config: object,
        _mock_list_remotes: object,
        _mock_access: object,
        _mock_save: object,
    ) -> None:
        mock_preflight.return_value = CheckResult(
            code=0,
            status="success",
            message="ok",
            rclone_version="1.75.1",
        )
        mock_load_config.return_value = AppConfig(remote=None, root="DriveSync")

        result = setup_auth("gdrive-personal:")
        self.assertEqual(result.code, 0)
        self.assertEqual(result.remote, "gdrive-personal")

    @patch("drivesync.auth._check_remote_access", return_value=False)
    @patch("drivesync.auth._list_rclone_remotes", return_value={"gdrive"})
    @patch("drivesync.auth.load_app_config")
    @patch("drivesync.auth.run_preflight_check")
    def test_setup_auth_remote_inaccessible(
        self,
        mock_preflight: object,
        mock_load_config: object,
        _mock_list_remotes: object,
        _mock_access: object,
    ) -> None:
        mock_preflight.return_value = CheckResult(
            code=0,
            status="success",
            message="ok",
            rclone_version="1.75.1",
        )
        mock_load_config.return_value = AppConfig(remote="gdrive")

        result = setup_auth()
        self.assertEqual(result.code, 2)
        self.assertIn("Impossible d'acceder", result.message)


if __name__ == "__main__":
    unittest.main()