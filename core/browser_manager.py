import json
import logging
import os
import re
import random as _random
from pathlib import Path

import playwright
from playwright.async_api import async_playwright
import config.settings as cfg


_LOG = logging.getLogger(__name__)
_MOBILES = (
    "iPhone 14 Pro", "iPhone 14 Pro Max", "iPhone 13 Mini",
    "Pixel 7", "Pixel 5", "Samsung Galaxy S22", "iPad Pro 11",
)
# Playwright has no S22 preset. Use an available Samsung preset explicitly.
_DEVICE_ALIASES = {"Samsung Galaxy S22": ("Galaxy S24", "Galaxy S9+")}


class BrowserManager:
    async def launch_browser(self):
        self.playwright = await async_playwright().start()
        self.devices = self.playwright.devices
        args = ["--mute-audio"]
        if "Desktop" in cfg.DEVICE_NAME:
            args.append("--start-maximized")
        try:
            launch_opts = {"headless": cfg.HEADLESS_MODE, "args": args}
            # Build installs browsers beside Playwright (PLAYWRIGHT_BROWSERS_PATH=0).
            # Also find that installation when running source from the build venv.
            executable = Path(self.playwright.chromium.executable_path)
            if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ and not executable.is_file():
                bundled = (
                    Path(playwright.__file__).parent / "driver" / "package" /
                    ".local-browsers" / executable.parent.parent.name /
                    executable.parent.name / executable.name
                )
                if bundled.is_file():
                    launch_opts["executable_path"] = str(bundled)
            self.browser = await self.playwright.chromium.launch(
                **launch_opts
            )
        except BaseException:
            await self.playwright.stop()
            raise
        return self.browser

    def _device_preset(self, name):
        if name in self.devices:
            return name
        return next(
            (alias for alias in _DEVICE_ALIASES.get(name, ()) if alias in self.devices),
            None,
        )

    async def create_context(self, browser, proxy_info=None, profile_id="default"):
        os.makedirs("profiles", exist_ok=True)
        safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", str(profile_id)).strip("_") or "default"
        state_file = os.path.join("profiles", f"state_{safe_id}.json")

        selected_device = cfg.DEVICE_NAME
        if selected_device.startswith("Random Mobile 70") or "70%" in selected_device:
            selected_device = "Random Mobile" if _random.random() < 0.7 else "Desktop"
        elif selected_device.startswith("Random Mobile"):
            selected_device = "Random Mobile"
        elif selected_device.startswith("Random"):
            selected_device = "Random Mobile" if _random.random() < 0.7 else "Desktop"

        if selected_device == "Random Mobile":
            available = [name for name in _MOBILES if self._device_preset(name)]
            selected_device = _random.choice(available) if available else "Desktop"

        device_config = {"viewport": dict(cfg.VIEWPORT_SIZE)}
        if "Desktop" not in selected_device:
            preset = self._device_preset(selected_device)
            if preset:
                # Mobile emulation runs in Chromium, even for iOS layout presets.
                device_config = dict(self.devices[preset])
                device_config.pop("default_browser_type", None)
                if preset != selected_device:
                    print(f"   [Browser] {selected_device}: dùng preset {preset} có sẵn.")
                selected_device = preset
            else:
                print(f"   [Browser] Không có preset {selected_device}; dùng Desktop.")
                selected_device = "Desktop"

        print(f"   [Browser] Chromium | preset: {selected_device} | locale: vi-VN")
        context_opts = {
            **device_config,
            "locale": "vi-VN",
            "timezone_id": "Asia/Ho_Chi_Minh",
            "extra_http_headers": {
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        }

        # New-user sessions must not restore cookies from an earlier visit.
        if not cfg.ALWAYS_NEW_USER and os.path.exists(state_file):
            try:
                with open(state_file, encoding="utf-8") as saved:
                    state = json.load(saved)
                if not isinstance(state, dict):
                    raise ValueError("storage state must be an object")
                if not isinstance(state.get("cookies"), list) or not isinstance(state.get("origins"), list):
                    raise ValueError("storage state must contain cookies and origins lists")
                context_opts["storage_state"] = state
            except (OSError, ValueError) as exc:
                _LOG.warning("Không đọc được profile %s; tạo phiên mới: %s", state_file, exc)

        if proxy_info:
            # Legacy format: host:port:user:password. Also accept URL proxies.
            parts = proxy_info.split(":", 3)
            if "://" not in proxy_info and len(parts) == 4:
                context_opts["proxy"] = {
                    "server": f"http://{parts[0]}:{parts[1]}",
                    "username": parts[2],
                    "password": parts[3],
                }
            else:
                context_opts["proxy"] = {"server": proxy_info}

        context = await browser.new_context(**context_opts)
        try:
            # UI and CLI save state before context.close(), while it is still usable.
            context._seo_state_file = state_file
            if not cfg.LOAD_IMAGES:
                async def route_request(route):
                    if route.request.resource_type == "image":
                        await route.abort()
                    else:
                        await route.continue_()
                await context.route("**/*", route_request)
            return await context.new_page()
        except BaseException:
            await context.close()
            raise

    async def close(self):
        try:
            if hasattr(self, "browser"):
                # Save contexts still open during shutdown, before closing the browser.
                for context in self.browser.contexts:
                    state_file = getattr(context, "_seo_state_file", None)
                    if state_file and not cfg.ALWAYS_NEW_USER:
                        try:
                            await context.storage_state(path=state_file)
                        except Exception as exc:
                            _LOG.warning("Không lưu được profile %s: %s", state_file, exc)
                await self.browser.close()
        finally:
            if hasattr(self, "playwright"):
                await self.playwright.stop()
