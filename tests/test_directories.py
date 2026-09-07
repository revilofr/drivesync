from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from drivesync.cli import main
from drivesync.config import get_directories_file
from drivesync.directories import DirectoryConfigError, add_directory, load_directories, remove_directory


class DriveSyncDirectoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name) / "config"
        self.docs_dir = Path(self.temp_dir.name) / "Documents"
        self.projects_dir = Path(self.temp_dir.name) / "Projects"
        self.docs_dir.mkdir()
        self.projects_dir.mkdir()
        self.original_config_home = os.environ.get("DRIVESYNC_CONFIG_HOME")
        os.environ["DRIVESYNC_CONFIG_HOME"] = str(self.config_dir)

    def tearDown(self) -> None:
        if self.original_config_home is None:
            os.environ.pop("DRIVESYNC_CONFIG_HOME", None)
        else:
            os.environ["DRIVESYNC_CONFIG_HOME"] = self.original_config_home
        self.temp_dir.cleanup()

    def test_add_and_load_directories(self) -> None:
        managed_directory = add_directory("documents", self.docs_dir)

        self.assertEqual(managed_directory.directory_id, "documents")
        self.assertEqual(managed_directory.directory, self.docs_dir.resolve())
        self.assertEqual(managed_directory.remote_subpath, "documents")
        self.assertEqual(
            load_directories(),
            [managed_directory],
        )

    def test_add_with_custom_remote_directory(self) -> None:
        managed_directory = add_directory("documents", self.docs_dir, "archives/documents")

        self.assertEqual(managed_directory.remote_subpath, "archives/documents")
        loaded = load_directories()
        self.assertEqual(loaded[0].remote_subpath, "archives/documents")

    def test_add_rejects_invalid_id(self) -> None:
        with self.assertRaises(DirectoryConfigError):
            add_directory("documents perso", self.docs_dir)

    def test_add_rejects_missing_directory(self) -> None:
        with self.assertRaises(DirectoryConfigError):
            add_directory("documents", Path(self.temp_dir.name) / "Missing")

    def test_cli_add_missing_directory_prompt_accept_creates_directory(self) -> None:
        missing = Path(self.temp_dir.name) / "MissingByPrompt"

        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="y"):
            exit_code = main(["dir", "add", "documents", str(missing)])

        self.assertEqual(exit_code, 0)
        self.assertTrue(missing.exists())
        self.assertEqual(load_directories()[0].directory_id, "documents")

    def test_cli_add_missing_directory_prompt_decline_returns_error(self) -> None:
        missing = Path(self.temp_dir.name) / "MissingDeclined"

        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", return_value="n"):
            exit_code = main(["dir", "add", "documents", str(missing)])

        self.assertEqual(exit_code, 2)
        self.assertFalse(missing.exists())
        self.assertEqual(load_directories(), [])

    def test_cli_add_missing_directory_create_flag(self) -> None:
        missing = Path(self.temp_dir.name) / "MissingWithFlag"

        exit_code = main(["dir", "add", "documents", str(missing), "--create"])

        self.assertEqual(exit_code, 0)
        self.assertTrue(missing.exists())
        self.assertEqual(load_directories()[0].directory_id, "documents")

    def test_add_rejects_duplicate_remote_directory(self) -> None:
        add_directory("documents", self.docs_dir, "shared/path")

        with self.assertRaises(DirectoryConfigError):
            add_directory("projects", self.projects_dir, "shared/path")

    def test_remove_directory(self) -> None:
        add_directory("documents", self.docs_dir)
        add_directory("projects", self.projects_dir)

        removed = remove_directory("documents")

        self.assertEqual(removed.directory_id, "documents")
        self.assertEqual(load_directories()[0].directory_id, "projects")

    def test_cli_list_json(self) -> None:
        add_directory("documents", self.docs_dir, "archives/documents")

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["dir", "list", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload,
            [
                {
                    "id": "documents",
                    "directory": str(self.docs_dir.resolve()),
                    "remote_directory": "archives/documents",
                }
            ],
        )

    def test_cli_show_json(self) -> None:
        add_directory("documents", self.docs_dir, "archives/documents")

        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["dir", "show", "documents", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["id"], "documents")
        self.assertEqual(payload["remote_directory"], "archives/documents")

    def test_cli_add_creates_config_file(self) -> None:
        exit_code = main(["dir", "add", "documents", str(self.docs_dir)])

        self.assertEqual(exit_code, 0)
        self.assertTrue(get_directories_file().exists())

    def test_load_directories_backward_compatible_format(self) -> None:
        get_directories_file().parent.mkdir(parents=True, exist_ok=True)
        get_directories_file().write_text(
            f"documents={self.docs_dir.resolve()}\n",
            encoding="utf-8",
        )

        loaded = load_directories()
        self.assertEqual(loaded[0].directory_id, "documents")
        self.assertEqual(loaded[0].remote_subpath, "documents")

    def test_load_directories_rejects_duplicate_remote_directory(self) -> None:
        get_directories_file().parent.mkdir(parents=True, exist_ok=True)
        get_directories_file().write_text(
            (
                f"documents={self.docs_dir.resolve()}|shared/path\n"
                f"projects={self.projects_dir.resolve()}|shared/path\n"
            ),
            encoding="utf-8",
        )

        with self.assertRaises(DirectoryConfigError):
            _ = load_directories()


if __name__ == "__main__":
    unittest.main()