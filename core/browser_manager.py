import os
import re
import random as _random
from playwright.async_api import async_playwright
import config.settings as cfg
class BrowserManager:
    async def launch_browser(self):
        self.playwright = await async_playwright().start()
        self.devices = self.playwright.devices

        args = ["--mute-audio"]

        # Desktop mới dùng start-maximized
        if cfg.DEVICE_NAME == "Desktop" or "Desktop" in cfg.DEVICE_NAME:
            args.append("--start-maximized")
        else:
            if "--start-maximized" in args:
                args.remove("--start-maximized")

        self.browser = await self.playwright.chromium.launch(
            headless=cfg.HEADLESS_MODE,
            args=args
        )
        return self.browser

    async def create_context(self, browser, proxy_info=None, profile_id="default"):
        if not os.path.exists("profiles"):
            os.makedirs("profiles")

        safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", str(profile_id)).strip("_") or "default"
        # ─── CHỌN DEVICE ────────────────────────────────────────────────────
        selected_device = cfg.DEVICE_NAME

        if "Random Mobile 70" in cfg.DEVICE_NAME or "70%" in cfg.DEVICE_NAME:
            selected_device = "Random Mobile" if _random.random() < 0.7 else "Desktop"
        elif selected_device.startswith("Random Mobile"):
            selected_device = "Random Mobile"
        elif selected_device.startswith("Random"):
            selected_device = "Random Mobile" if _random.random() < 0.7 else "Desktop"

        _MOBILES = ["iPhone 14 Pro", "iPhone 14 Pro Max", "iPhone 13 Mini",
                    "Pixel 7", "Pixel 5", "Samsung Galaxy S22", "iPad Pro 11"]

        if selected_device == "Random Mobile":
            selected_device = _random.choice(_MOBILES)

        # Device presets are used only for layout dimensions. Browser identity,
        # platform, GPU and hardware properties remain native to Chromium.
        viewport = cfg.VIEWPORT_SIZE
        if selected_device in self.devices:
            viewport = dict(self.devices[selected_device]["viewport"])
        context_opts = {"viewport": viewport}
        print(f"   [Browser] Native Chromium | viewport: {viewport['width']}x{viewport['height']} | preset: {selected_device}")

        # Lưu profile riêng cho mỗi context (lưu cookie/localStorage giữa các lần chạy)
        # Giúp Google nhận ra browser quen thuộc, giảm CAPTCHA
        try:
            profile_state = f"profiles/state_{safe_id}.json"
            if os.path.exists(profile_state):
                context_opts["storage_state"] = profile_state
        except:
            pass

        # ─── PROXY ──────────────────────────────────────────────────────────
        if proxy_info:
            parts = proxy_info.split(":")
            if len(parts) == 4:
                context_opts["proxy"] = {
                    "server": f"http://{parts[0]}:{parts[1]}",
                    "username": parts[2],
                    "password": parts[3],
                }
            else:
                context_opts["proxy"] = {"server": proxy_info}

        # STORAGE STATE sẽ được set khi auto-save sau này

        context = await browser.new_context(**context_opts)

        if not cfg.LOAD_IMAGES:
            await context.route(
                "**/*",
                lambda route: route.abort()
                if route.request.resource_type == "image"
                else route.continue_(),
            )

        page = await context.new_page()

        # UI se luu state truoc khi dong context. Gan duong dan vao context
        # de tranh callback async chay sau khi Playwright da dung.
        context._seo_state_file = f"profiles/state_{safe_id}.json"

        return page

    async def close(self):
        if hasattr(self, 'browser'):
            try:
                await self.browser.close()
            except:
                pass
        if hasattr(self, 'playwright'):
            try:
                await self.playwright.stop()
            except:
                pass
