"""Local Chromium smoke tests; no external websites or traffic are used."""
import asyncio
import base64
import os
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import config.settings as cfg
from core.browser_manager import BrowserManager
from utils.targets import get_target_url
import ui


class BrowserRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        original_cwd = os.getcwd()
        os.chdir(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(os.chdir, original_cwd)
        for name, value in (("HEADLESS_MODE", True), ("ALWAYS_NEW_USER", False), ("DEVICE_NAME", "Desktop")):
            setting = patch.object(cfg, name, value)
            setting.start()
            self.addCleanup(setting.stop)
        self.manager = BrowserManager()
        self.browser = await self.manager.launch_browser()
        self.addAsyncCleanup(self.manager.close)
        self.requests = []
        self.server = await asyncio.start_server(self.respond, "127.0.0.1", 0)
        self.addAsyncCleanup(self.stop_server)
        self.url = f"http://127.0.0.1:{self.server.sockets[0].getsockname()[1]}"

    async def stop_server(self):
        self.server.close()
        await self.server.wait_closed()

    async def respond(self, reader, writer):
        try:
            request = await reader.readuntil(b"\r\n\r\n")
            path = request.split(b" ")[1].decode()
            self.requests.append(path)
            if path.startswith("/image.png"):
                body = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aMioAAAAASUVORK5CYII=")
                content_type = "image/png"
            else:
                body = b'<html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><img src="/image.png"></body></html>'
                content_type = "text/html"
            header = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n"
            writer.write(header.encode() + body)
            await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            # Chromium may open a speculative connection without an HTTP request.
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    async def test_all_ui_devices_keep_browser_apis_working(self):
        for device in cfg.SUPPORTED_DEVICES:
            with self.subTest(device=device), patch.object(cfg, "DEVICE_NAME", device):
                page = await self.manager.create_context(self.browser, profile_id="apis")
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                await page.goto(self.url)
                result = await page.evaluate("""async () => {
                    const gl = document.createElement('canvas').getContext('webgl');
                    const permission = await navigator.permissions.query({name:'geolocation'});
                    const notifications = await navigator.permissions.query({name:'notifications'});
                    return {
                        textureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
                        permission: permission instanceof PermissionStatus,
                        notifications: notifications instanceof PermissionStatus,
                        plugins: navigator.plugins instanceof PluginArray,
                        cores: Array.from({length:20}, () => navigator.hardwareConcurrency),
                        locale: navigator.language,
                    };
                }""")
                self.assertFalse(errors)
                self.assertGreater(result["textureSize"], 0)
                self.assertTrue(result["permission"])
                self.assertTrue(result["notifications"])
                self.assertTrue(result["plugins"])
                self.assertEqual(len(set(result["cores"])), 1)
                self.assertEqual(result["locale"], "vi-VN")
                await page.context.close()

    async def test_shutdown_persists_cookie_and_new_user_does_not_restore_it(self):
        page = await self.manager.create_context(self.browser, profile_id="cookie")
        await page.context.add_cookies([{"name": "probe", "value": "saved", "url": self.url}])
        await self.manager.close()
        self.assertTrue(Path("profiles/state_cookie.json").is_file())
        self.browser = await self.manager.launch_browser()
        page = await self.manager.create_context(self.browser, profile_id="cookie")
        self.assertTrue(any(c["name"] == "probe" for c in await page.context.cookies()))
        await page.context.close()
        with patch.object(cfg, "ALWAYS_NEW_USER", True):
            page = await self.manager.create_context(self.browser, profile_id="cookie")
            self.assertFalse(await page.context.cookies())
            await page.context.close()

    async def test_images_follow_setting_and_document_still_loads(self):
        for enabled in (False, True):
            with patch.object(cfg, "LOAD_IMAGES", enabled):
                page = await self.manager.create_context(self.browser, profile_id="images")
                self.requests.clear()
                await page.goto(self.url)
                self.assertIn("/", self.requests)
                self.assertEqual("/image.png" in self.requests, enabled)
                await page.context.close()

    async def test_session_navigates_to_both_local_targets_in_same_context(self):
        visits = []
        async def visit(page, duration):
            await page.goto(get_target_url())
            visits.append((page.url, page.context))
            return True
        app = SimpleNamespace(stop_event=threading.Event(), after=lambda *args: None, _inc_ok=lambda: None, _inc_err=lambda: None)
        targets = [self.url + "/first", self.url + "/second"]
        with patch.object(cfg, "TARGET_URLS", targets), patch.object(cfg, "WARMUP_ENABLE", False), patch.object(cfg, "TRAFFIC_MODE", "direct"), patch("utils.rate_limiter.acquire_session", return_value=(True, "")), patch.object(ui, "run_deep_session", side_effect=visit):
            await ui.ZizaSeoUI.process_single_session(app, self.manager, self.browser, None, 1)
        self.assertEqual([url for url, context in visits], targets)
        self.assertIs(visits[0][1], visits[1][1])
        self.assertIn("/first", self.requests)
        self.assertIn("/second", self.requests)
