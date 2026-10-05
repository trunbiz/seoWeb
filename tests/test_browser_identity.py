import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import config.settings as cfg
from core.browser_manager import BrowserManager

class BrowserIdentityTests(unittest.IsolatedAsyncioTestCase):
    async def test_presets_change_only_viewport(self):
        manager = BrowserManager()
        manager.devices = {"iPhone 14 Pro": {"viewport": {"width": 393, "height": 659}, "user_agent": "fake Safari", "is_mobile": True, "has_touch": True, "device_scale_factor": 3}}
        for device in ("Desktop", "iPhone 14 Pro"):
            context = SimpleNamespace(new_page=AsyncMock(return_value=object()), route=AsyncMock(), add_init_script=AsyncMock())
            browser = SimpleNamespace(new_context=AsyncMock(return_value=context))
            with patch.object(cfg, "DEVICE_NAME", device), patch.object(cfg, "LOAD_IMAGES", True), patch("core.browser_manager.os.path.exists", return_value=True), patch("builtins.print"):
                await manager.create_context(browser)
            options = browser.new_context.call_args.kwargs
            self.assertEqual(set(options), {"viewport", "storage_state"})
            if device == "iPhone 14 Pro":
                self.assertEqual(options["viewport"], {"width": 393, "height": 659})
            context.add_init_script.assert_not_called()

    async def test_launch_keeps_default_automation_flags(self):
        manager = BrowserManager()
        chromium = SimpleNamespace(launch=AsyncMock())
        runtime = SimpleNamespace(devices={}, chromium=chromium)
        with patch("core.browser_manager.async_playwright", return_value=SimpleNamespace(start=AsyncMock(return_value=runtime))):
            await manager.launch_browser()
        args = chromium.launch.call_args.kwargs["args"]
        self.assertNotIn("--disable-blink-features=AutomationControlled", args)
        self.assertNotIn("--disable-web-security", args)
