import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from utils.user_settings import load_settings, save_settings


@unittest.skipUnless(os.name == "nt", "Windows DPAPI")
class UserSettingsTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "settings.dat"

    def test_roundtrip_protects_secrets_and_preserves_values(self):
        values = {"entry_aibox_key": "test-secret-key", "txt_keywords": "từ khóa\ndòng 2",
                  "chk_warmup": 0, "slider_threads": 7, "entry_url": ""}
        self.assertEqual(load_settings(self.path), {})
        save_settings(values, self.path)
        self.assertNotIn(b"test-secret-key", self.path.read_bytes())
        self.assertEqual(load_settings(self.path), values)

    def test_failed_write_keeps_previous_settings(self):
        save_settings({"value": "old"}, self.path)
        with patch("utils.user_settings.os.replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                save_settings({"value": "new"}, self.path)
        self.assertEqual(load_settings(self.path), {"value": "old"})
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_corrupt_file_reports_error(self):
        self.path.write_bytes(b"broken")
        with self.assertRaises(OSError):
            load_settings(self.path)
