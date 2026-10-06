import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import config.settings as cfg
from core.browser_manager import BrowserManager


class BrowserIdentityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        original_cwd = os.getcwd()
        os.chdir(self.temp.name)
        self.addCleanup(os.chdir, original_cwd)
        self.manager = BrowserManager()
        self.manager.devices = {
            "iPhone 14 Pro": {
                "viewport": {"width": 393, "height": 659}, "user_agent": "Safari preset",
                "is_mobile": True, "has_touch": True, "device_scale_factor": 3,
                "default_browser_type": "webkit",
            },
            "Galaxy S24": {"viewport": {"width": 360, "height": 780}, "is_mobile": True, "has_touch": True},
        }
        self.page = object()
        self.context = SimpleNamespace(
            new_page=AsyncMock(return_value=self.page), route=AsyncMock(),
            add_init_script=AsyncMock(), close=AsyncMock(), storage_state=AsyncMock(),
        )
        self.browser = SimpleNamespace(new_context=AsyncMock(return_value=self.context))

    async def create(self, device, **kwargs):
        with patch.object(cfg, "DEVICE_NAME", device), patch("builtins.print"):
            return await self.manager.create_context(self.browser, **kwargs)

    async def test_desktop_keeps_native_identity_and_mobile_uses_emulation(self):
        await self.create("Desktop")
        options = self.browser.new_context.call_args.kwargs
        self.assertNotIn("user_agent", options)
        self.assertEqual(options["locale"], "vi-VN")
        self.assertNotIn("ignore_https_errors", options)
        await self.create("iPhone 14 Pro")
        options = self.browser.new_context.call_args.kwargs
        self.assertTrue(options["is_mobile"])
        self.assertTrue(options["has_touch"])
        self.assertEqual(options["viewport"], {"width": 393, "height": 659})
        self.assertNotIn("default_browser_type", options)
        self.context.add_init_script.assert_not_called()

    async def test_random_mobile_ui_label_never_falls_back_to_desktop(self):
        with patch("core.browser_manager._random.choice", return_value="iPhone 14 Pro"):
            await self.create("Random Mobile (Chỉ điện thoại)")
        self.assertTrue(self.browser.new_context.call_args.kwargs["is_mobile"])

    async def test_mixed_random_labels_select_both_branches(self):
        for label in ("Random (Ngẫu nhiên mọi loại)", "Random Mobile 70 (70% mobile, 30% desktop)"):
            for value, mobile in ((0.1, True), (0.9, False)):
                with patch("core.browser_manager._random.random", return_value=value), patch("core.browser_manager._random.choice", return_value="iPhone 14 Pro"):
                    await self.create(label)
                self.assertEqual(self.browser.new_context.call_args.kwargs.get("is_mobile", False), mobile)

    async def test_samsung_uses_available_samsung_preset(self):
        await self.create("Samsung Galaxy S22")
        self.assertTrue(self.browser.new_context.call_args.kwargs["is_mobile"])

    async def test_image_filter_blocks_only_images(self):
        with patch.object(cfg, "LOAD_IMAGES", False):
            await self.create("Desktop")
        callback = self.context.route.call_args.args[1]
        route = SimpleNamespace(request=SimpleNamespace(resource_type="image"), abort=AsyncMock(), continue_=AsyncMock())
        await callback(route)
        route.abort.assert_awaited_once()
        route.request.resource_type = "script"
        await callback(route)
        route.continue_.assert_awaited_once()

    async def test_profile_restored_only_for_returning_user(self):
        profile = Path(self.temp.name, "profiles", "state_default.json")
        profile.parent.mkdir(exist_ok=True)
        state = {"cookies": [], "origins": []}
        profile.write_text(json.dumps(state))
        for new_user in (False, True):
            with patch.object(cfg, "ALWAYS_NEW_USER", new_user):
                await self.create("Desktop")
            options = self.browser.new_context.call_args.kwargs
            self.assertEqual("storage_state" in options, not new_user)
            self.assertEqual(Path(self.context._seo_state_file).resolve(), profile)

    async def test_corrupt_profile_starts_fresh(self):
        profile = Path(self.temp.name, "profiles", "state_default.json")
        profile.parent.mkdir(exist_ok=True)
        profile.write_text("broken json")
        with patch.object(cfg, "ALWAYS_NEW_USER", False), self.assertLogs("core.browser_manager", level="WARNING"):
            await self.create("Desktop")
        self.assertNotIn("storage_state", self.browser.new_context.call_args.kwargs)

    async def test_profile_id_cannot_create_nested_paths(self):
        await self.create("Desktop", profile_id="../../worker\\one:123")
        path = Path(self.context._seo_state_file).resolve()
        self.assertEqual(path.parent, Path(self.temp.name, "profiles"))

    async def test_proxy_password_keeps_colons(self):
        await self.create("Desktop", proxy_info="host:8080:user:pass:word")
        self.assertEqual(self.browser.new_context.call_args.kwargs["proxy"]["password"], "pass:word")
        await self.create("Desktop", proxy_info="http://host:8080")
        self.assertEqual(self.browser.new_context.call_args.kwargs["proxy"], {"server": "http://host:8080"})

    async def test_context_closed_if_page_creation_fails(self):
        self.context.new_page.side_effect = RuntimeError("page failed")
        with self.assertRaisesRegex(RuntimeError, "page failed"):
            await self.create("Desktop")
        self.context.close.assert_awaited_once()

    async def test_shutdown_saves_before_browser_close(self):
        order = []
        self.context._seo_state_file = "state.json"
        async def save(**kwargs):
            order.append("save")
        async def close():
            order.append("close")
        self.context.storage_state.side_effect = save
        self.manager.browser = SimpleNamespace(contexts=[self.context], close=AsyncMock(side_effect=close))
        self.manager.playwright = SimpleNamespace(stop=AsyncMock())
        with patch.object(cfg, "ALWAYS_NEW_USER", False):
            await self.manager.close()
        self.assertEqual(order, ["save", "close"])
        self.manager.playwright.stop.assert_awaited_once()

    async def test_launch_keeps_default_automation_flags(self):
        chromium = SimpleNamespace(launch=AsyncMock(), executable_path=str(Path(__file__).resolve()))
        runtime = SimpleNamespace(devices={}, chromium=chromium, stop=AsyncMock())
        with patch("core.browser_manager.async_playwright", return_value=SimpleNamespace(start=AsyncMock(return_value=runtime))):
            await self.manager.launch_browser()
        args = chromium.launch.call_args.kwargs["args"]
        self.assertNotIn("--disable-blink-features=AutomationControlled", args)
        self.assertNotIn("--disable-web-security", args)

    async def test_failed_launch_stops_playwright(self):
        chromium = SimpleNamespace(launch=AsyncMock(side_effect=RuntimeError("launch failed")), executable_path=str(Path(__file__).resolve()))
        runtime = SimpleNamespace(devices={}, chromium=chromium, stop=AsyncMock())
        with patch("core.browser_manager.async_playwright", return_value=SimpleNamespace(start=AsyncMock(return_value=runtime))):
            with self.assertRaisesRegex(RuntimeError, "launch failed"):
                await self.manager.launch_browser()
        runtime.stop.assert_awaited_once()
