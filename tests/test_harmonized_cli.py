from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from drivesync.cli import main


class HarmonizedCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name) / "cfg"
        self.original_config_home = os.environ.get("DRIVESYNC_CONFIG_HOME")
        os.environ["DRIVESYNC_CONFIG_HOME"] = str(self.config_dir)

    def tearDown(self) -> None:
        if self.original_config_home is None:
            os.environ.pop("DRIVESYNC_CONFIG_HOME", None)
        else:
            os.environ["DRIVESYNC_CONFIG_HOME"] = self.original_config_home
        self.temp_dir.cleanup()

    def test_sync_status_empty_text(self) -> None:
        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "status"])

            stdout.seek(0)
            output = stdout.read().strip()

        self.assertEqual(exit_code, 0)
        self.assertEqual(output, "0|empty|Aucun repertoire configure")

    def test_sync_logs_json(self) -> None:
        with tempfile.TemporaryFile(mode="w+") as stdout:
            from contextlib import redirect_stdout

            with redirect_stdout(stdout):
                exit_code = main(["sync", "logs", "--json"])

            stdout.seek(0)
            payload = json.load(stdout)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["count"], 0)


if __name__ == "__main__":
    unittest.main()