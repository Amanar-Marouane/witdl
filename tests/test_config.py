"""Tests for witdl.config."""

import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from witdl.config import Config


class TestConfigDefaults(unittest.TestCase):
    def test_default_values(self):
        config = Config()
        self.assertEqual(config.quality, "fhd")
        self.assertEqual(config.max_concurrent_downloads, 2)
        self.assertEqual(config.delay_between_episodes, 2.0)
        self.assertEqual(config.timeout_per_download, 900)
        self.assertTrue(config.auto_retry)
        self.assertEqual(config.max_retries, 3)
        self.assertIn("mediafire", config.hoster_priority)
        self.assertIn("hexload", config.hoster_priority)

    def test_default_hoster_priority_order(self):
        config = Config()
        self.assertEqual(config.hoster_priority[0], "mediafire")
        self.assertEqual(config.hoster_priority[1], "hexload")


class TestConfigSaveLoad(unittest.TestCase):
    def test_save_and_load(self):
        test_dir = tempfile.mkdtemp()
        config_file = Path(test_dir) / "config.json"

        import witdl.config as config_mod
        original = config_mod.CONFIG_FILE
        config_mod.CONFIG_FILE = config_file

        try:
            config = Config(download_dir="/tmp/test", quality="sd", max_concurrent_downloads=4)
            config.save()

            loaded = Config.load()
            self.assertEqual(loaded.download_dir, "/tmp/test")
            self.assertEqual(loaded.quality, "sd")
            self.assertEqual(loaded.max_concurrent_downloads, 4)
        finally:
            config_mod.CONFIG_FILE = original
            config_file.unlink(missing_ok=True)

    def test_load_returns_defaults_on_missing_file(self):
        import witdl.config as config_mod
        original = config_mod.CONFIG_FILE
        config_mod.CONFIG_FILE = Path("/tmp/nonexistent_witdl_config_test.json")

        try:
            config = Config.load()
            self.assertEqual(config.quality, "fhd")
        finally:
            config_mod.CONFIG_FILE = original

    def test_load_returns_defaults_on_corrupt_file(self):
        import witdl.config as config_mod
        original = config_mod.CONFIG_FILE
        corrupt_file = Path(tempfile.mktemp(suffix=".json"))
        corrupt_file.write_text("not valid json {{{")

        config_mod.CONFIG_FILE = corrupt_file
        try:
            config = Config.load()
            self.assertEqual(config.quality, "fhd")
        finally:
            config_mod.CONFIG_FILE = original
            corrupt_file.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
