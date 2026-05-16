import os
import asyncio
import random as _random
from playwright.async_api import async_playwright
from fake_useragent import UserAgent
import config.settings as cfg

try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None


# ─── ANTI-DETECT: Script chống phát hiện Playwright ─────────────────────────
_ANTI_DETECT_SCRIPT = """
// 1. Che webdriver
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// 2. Che Chrome runtime (phát hiện automation)
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {},
    webstore: {}
};

// 3. Che plugins (trình duyệt automation thường 0 plugin)
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5].map(() => ({name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'})),
});

// 4. Che languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['vi-VN', 'vi', 'en-US', 'en'],
});

// 5. Thêm deviceMemory, hardwareConcurrency thật
Object.defineProperty(navigator, 'deviceMemory', {get: () => [4, 8][Math.floor(Math.random() * 2)]});
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => [4, 6, 8, 12][Math.floor(Math.random() * 4)]});

// 6. WebGL - chặn canvas fingerprinting
try {
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter(parameter);
    };
} catch(e) {}

// 7. Che permissions (tránh navigator.permissions.query mismatch)
try {
    const originalQuery = navigator.permissions.query;
    navigator.permissions.query = (params) => (
        params.name === 'notifications' || params.name === 'clipboard-read' || params.name === 'clipboard-write'
        ? Promise.resolve({state: 'prompt', onchange: null})
        : originalQuery(params)
    );
} catch(e) {}

// 8. Thêm screen độ phân giải phổ biến (cho Desktop)
try {
    if (!navigator.maxTouchPoints) {
        Object.defineProperty(screen, 'colorDepth', {get: () => 24});
        Object.defineProperty(screen, 'pixelDepth', {get: () => 24});
    }
} catch(e) {}

// 9. Xoá dấu vết của Playwright trong stack trace
try {
    const oldToString = Error.prototype.toString;
    Error.prototype.toString = function() {
        return oldToString.call(this).replace(/\\n.*playwright.*\\n?/g, '');
    };
} catch(e) {}
"""


class BrowserManager:
    def __init__(self):
        try:
            self.ua = UserAgent(browsers=['chrome'])
        except:
            self.ua = None

    async def launch_browser(self):
        self.playwright = await async_playwright().start()
        self.devices = self.playwright.devices

        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox",
            "--disable-webrtc",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-sync",
            "--disable-background-networking",
            "--disable-default-apps",
            "--no-first-run",
            "--disable-background-timer-throttling",
            "--disable-client-side-phishing-detection",
            "--disable-component-update",
            "--disable-field-trial-config",
            "--disable-prompt-on-repost",
            "--disable-speech-api",
            "--hide-scrollbars",
            "--metrics-recording-only",
            "--mute-audio",
            "--no-default-browser-check",
        ]

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

        safe_id = str(profile_id).replace(":", "_").replace("@", "_").replace(".", "_")
        state_path = f"profiles/{safe_id}.json"

        # ─── CHỌN DEVICE ────────────────────────────────────────────────────
        device_config = {}
        selected_device = cfg.DEVICE_NAME

        if "Random Mobile 70" in cfg.DEVICE_NAME or "70%" in cfg.DEVICE_NAME:
            selected_device = "Random Mobile" if _random.random() < 0.7 else "Desktop"

        _MOBILES = ["iPhone 14 Pro", "iPhone 14 Pro Max", "iPhone 13 Mini",
                    "Pixel 7", "Pixel 5", "Samsung Galaxy S22", "iPad Pro 11"]

        if selected_device == "Random Mobile":
            selected_device = _random.choice(_MOBILES)

        is_desktop = False
        if selected_device == "Desktop":
            is_desktop = True

        if not is_desktop:
            # ── MOBILE ──────────────────────────────────────────────────────
            if selected_device in self.devices:
                device_config = dict(self.devices[selected_device])
                print(f"   [📱] Giả lập: {selected_device} (VN)")
            else:
                print(f"   [⚠️] Không tìm thấy device '{selected_device}', fallback Desktop.")
                is_desktop = True

        # ── LUÔN force locale/timezone VN ────────────────────────────────
        # Đây là nguyên nhân chính gây CAPTCHA: trước đây không set locale US
        if is_desktop:
            ua_vn = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
            # Dùng fake_useragent nhưng filter lấy Chrome Windows
            if self.ua:
                try:
                    ua_vn = self.ua.random
                except:
                    pass
            device_config = {
                "viewport": cfg.VIEWPORT_SIZE,
                "user_agent": ua_vn,
                "has_touch": False,
                "is_mobile": False,
            }
            print(f"   [💻] Desktop (VN)")

        # Force Vietnamese locale/timezone cho mọi trường hợp
        device_config["locale"] = "vi-VN"
        device_config["timezone_id"] = "Asia/Ho_Chi_Minh"

        # ─── MERGE ──────────────────────────────────────────────────────────
        context_opts = {
            **device_config,
            "ignore_https_errors": True,
            "permissions": ["geolocation"],
        }

        # Accept-Language header (quan trọng với Google)
        context_opts["extra_http_headers"] = {
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        }

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

        # ─── TIÊM SCRIPT CHỐNG PHÁT HIỆN ────────────────────────────────────
        await context.add_init_script(_ANTI_DETECT_SCRIPT)

        page = await context.new_page()
        if stealth_async:
            try:
                await stealth_async(page)
            except:
                pass

        # ─── AUTO SAVE (giữ cookie/state cho lần sau) ──────────────────────
        _state_file = f"profiles/state_{safe_id}.json"
        async def _save_state():
            try:
                await context.storage_state(path=_state_file)
            except:
                pass
        context.on("close", lambda: asyncio.create_task(_save_state()))

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
