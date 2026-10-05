import sys
import unittest
from unittest.mock import patch

import ui


class ZizaSeoUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.streams = sys.stdout, sys.stderr
        cls.loader = patch.object(ui, "load_settings", return_value={})
        cls.saver = patch.object(ui, "save_settings")
        cls.loader.start()
        cls.saver.start()
        cls.app = ui.ZizaSeoUI()
        cls.app.withdraw()
        sys.stdout, sys.stderr = cls.streams

    @classmethod
    def tearDownClass(cls):
        cls.app._close_window()
        cls.loader.stop()
        cls.saver.stop()
        sys.stdout, sys.stderr = cls.streams

    def test_brand_and_provider_panels(self):
        app = self.app
        self.assertIn("ZizaSeo", app.title())
        for provider in ("gemini", "aibox", "maxmorus", "local"):
            app.combo_ai_provider.set(provider)
            app._select_ai_provider(provider)
            for name, widgets in app._ai_provider_widgets.items():
                self.assertTrue(all(bool(widget.grid_info()) == (name == provider) for widget in widgets))

    def test_logs_readonly_bounded_and_collapsible(self):
        app = self.app
        app._clear_log()
        redirect = ui.RedirectText(app.txt_log, app)
        redirect._insert_text("example log\n" * 3100)
        self.assertEqual(app.txt_log._textbox.cget("state"), "disabled")
        self.assertLessEqual(int(app.txt_log.index("end-1c").split(".")[0]), 3001)
        app._toggle_log()
        self.assertFalse(app.txt_log.grid_info())
        app._toggle_log()
        self.assertTrue(app.txt_log.grid_info())
        app._clear_log()
        self.assertEqual(app.txt_log.get("1.0", "end-1c"), "")

    def test_invalid_url_does_not_start_worker(self):
        app = self.app
        original = app.entry_url.get()
        app.entry_url.delete(0, "end")
        app.entry_url.insert(0, "invalid-url")
        try:
            with patch.object(ui.messagebox, "showerror") as error, patch.object(ui.threading, "Thread") as worker:
                app.start_thread()
            error.assert_called_once()
            worker.assert_not_called()
            self.assertFalse(app.is_running)
        finally:
            app.entry_url.delete(0, "end")
            app.entry_url.insert(0, original)

    def test_saved_fields_survive_layout_change(self):
        app = self.app
        values = app._collect_settings()
        values.update(entry_url="https://saved.example/", entry_loop_time="120", chk_continuous=1,
                      combo_ai_provider="aibox", entry_aibox_key="dummy-key", chk_ytb=0)
        with patch.object(ui, "load_settings", return_value=values):
            app._restore_settings()
        self.assertEqual(app.entry_url.get(), values["entry_url"])
        self.assertEqual(app.entry_aibox_key.get(), "dummy-key")
        self.assertEqual(app.entry_loop_time.get(), "120")
        self.assertEqual(app.entry_loop_time.cget("state"), "disabled")
        self.assertEqual(app.chk_ytb.get(), 0)
        self.assertTrue(app.entry_aibox_key.grid_info())
