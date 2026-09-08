from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from drivesync.cli import main


class ConfigCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name) / "custom-config"
        self.home_dir = Path(self.temp_dir.name) / "home"
        self.home_dir.mkdir(parents=True, exist_ok=True)
        self.original_config_home = os.environ.get("DRIVESYNC_CONFIG_HOME")
        self.original_home = os.environ.get("HOME")
        self.original_xdg = os.environ.get("XDG_CONFIG_HOME")
        os.environ["DRIVESYNC_CONFIG_HOME"] = str(self.config_dir)
        os.environ["HOME"] = str(self.home_dir)
        os.environ.pop("XDG_CONFIG_HOME", None)

    def tearDown(self) -> None:
        if self.original_config_home is None:
            os.environ.pop("DRIVESYNC_CONFIG_HOME", None)
        else:
            os.environ["DRIVESYNC_CONFIG_HOME"] = self.original_config_home
        if self.original_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self.original_home
        if self.original_xdg is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = self.original_xdg
        self.temp_dir.cleanup()

    def test_config_path_json(self) -> None:
        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["config", "path", "show", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["config_dir"], str(self.config_dir.resolve()))
        self.assertTrue(payload["directories_file"].endswith("directories.conf"))
        self.assertTrue(payload["sync_history_file"].endswith("sync-history.jsonl"))
        self.assertTrue(payload["schedules_file"].endswith("schedules.json"))

    def test_config_path_set_and_reset(self) -> None:
        os.environ.pop("DRIVESYNC_CONFIG_HOME", None)
        custom_dir = Path(self.temp_dir.name) / "via-cli"

        set_exit = main(["config", "path", "set", str(custom_dir)])
        self.assertEqual(set_exit, 0)

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["config", "path", "show", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["config_dir"], str(custom_dir.resolve()))
        self.assertEqual(payload["source"], "config")

        reset_exit = main(["config", "path", "reset"])
        self.assertEqual(reset_exit, 0)

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["config", "path", "show", "--json"])

            stdout.seek(0)
            reset_payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(reset_payload["source"], "default")

    def test_config_logs_precision_defaults_to_light(self) -> None:
        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["config", "logs", "precision", "show", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["precision"], "light")

    def test_config_logs_precision_set_full(self) -> None:
        exit_code = main(["config", "logs", "precision", "set", "full"])
        self.assertEqual(exit_code, 0)

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                show_exit_code = main(["config", "logs", "precision", "show", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(show_exit_code, 0)
        self.assertEqual(payload["precision"], "full")

    def test_config_logs_max_size_defaults_to_10_kb(self) -> None:
        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["config", "logs", "max-size", "show", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["max_size_kb"], 10)

    def test_config_logs_max_size_set(self) -> None:
        exit_code = main(["config", "logs", "max-size", "set", "64"])
        self.assertEqual(exit_code, 0)

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                show_exit_code = main(["config", "logs", "max-size", "show", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(show_exit_code, 0)
        self.assertEqual(payload["max_size_kb"], 64)

    def test_config_root_defaults_to_drivesync(self) -> None:
        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["config", "root", "show", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["root"], "DriveSync")

    def test_config_root_set_and_reset(self) -> None:
        set_exit_code = main(["config", "root", "set", "Backups/DriveSync"])
        self.assertEqual(set_exit_code, 0)

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                show_exit_code = main(["config", "root", "show", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(show_exit_code, 0)
        self.assertEqual(payload["root"], "Backups/DriveSync")

        reset_exit_code = main(["config", "root", "reset"])
        self.assertEqual(reset_exit_code, 0)

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                reset_show_exit_code = main(["config", "root", "show", "--json"])

            stdout.seek(0)
            reset_payload = json.load(stdout)

        self.assertEqual(reset_show_exit_code, 0)
        self.assertEqual(reset_payload["root"], "DriveSync")


if __name__ == "__main__":
    unittest.main()