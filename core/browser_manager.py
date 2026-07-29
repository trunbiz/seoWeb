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


# ─── DEVICE FINGERPRINT MAP ────────────────────────────────────────────────────
# GPU vendor/renderer, CPU cores, RAM (GB), platform string cho từng thiết bị
_DEVICE_FINGERPRINTS = {
    "iPhone 14 Pro": {
        "gpu_vendor": "Apple Inc.",
        "gpu_renderer": "Apple GPU",
        "cores": 6,
        "ram": 6,
        "platform": "iPhone",
        "has_chrome": False,
        "has_plugins": False,
    },
    "iPhone 14 Pro Max": {
        "gpu_vendor": "Apple Inc.",
        "gpu_renderer": "Apple GPU",
        "cores": 6,
        "ram": 6,
        "platform": "iPhone",
        "has_chrome": False,
        "has_plugins": False,
    },
    "iPhone 13 Mini": {
        "gpu_vendor": "Apple Inc.",
        "gpu_renderer": "Apple GPU",
        "cores": 6,
        "ram": 4,
        "platform": "iPhone",
        "has_chrome": False,
        "has_plugins": False,
    },
    "Pixel 7": {
        "gpu_vendor": "Google",
        "gpu_renderer": "Google Tensor (ARM Mali-G710)",
        "cores": 8,
        "ram": 8,
        "platform": "Linux armv8l",
        "has_chrome": True,
        "has_plugins": True,
    },
    "Pixel 5": {
        "gpu_vendor": "Qualcomm",
        "gpu_renderer": "Adreno 620",
        "cores": 8,
        "ram": 8,
        "platform": "Linux armv8l",
        "has_chrome": True,
        "has_plugins": True,
    },
    "Samsung Galaxy S22": {
        "gpu_vendor": "Samsung",
        "gpu_renderer": "Xclipse 920",
        "cores": 8,
        "ram": 8,
        "platform": "Linux armv8l",
        "has_chrome": True,
        "has_plugins": True,
    },
    "iPad Pro 11": {
        "gpu_vendor": "Apple Inc.",
        "gpu_renderer": "Apple GPU",
        "cores": 8,
        "ram": 8,
        "platform": "iPad",
        "has_chrome": False,
        "has_plugins": False,
    },
    # Fallback cho mobile nếu không tìm thấy device cụ thể
    "Mobile fallback": {
        "gpu_vendor": "ARM",
        "gpu_renderer": "Mali-G76",
        "cores": 8,
        "ram": 6,
        "platform": "Linux armv8l",
        "has_chrome": True,
        "has_plugins": True,
    },
}


# ─── BASE ANTI-DETECT: dùng chung cho cả Desktop & Mobile ──────────────────
_BASE_SCRIPT = """
// 1. Che webdriver
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// 2. Che languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['vi-VN', 'vi', 'en-US', 'en'],
});

// 3. Che permissions (tránh navigator.permissions.query mismatch)
try {
    const originalQuery = navigator.permissions.query;
    navigator.permissions.query = (params) => (
        params.name === 'notifications' || params.name === 'clipboard-read' || params.name === 'clipboard-write'
        ? Promise.resolve({state: 'prompt', onchange: null})
        : originalQuery(params)
    );
} catch(e) {}

// 4. Thêm screen properties
try {
    Object.defineProperty(screen, 'colorDepth', {get: () => 24});
    Object.defineProperty(screen, 'pixelDepth', {get: () => 24});
} catch(e) {}

// 5. Xoá dấu vết của Playwright trong stack trace
try {
    const oldToString = Error.prototype.toString;
    Error.prototype.toString = function() {
        return oldToString.call(this).replace(/\\n.*playwright.*\\n?/g, '');
    };
} catch(e) {}
"""


# ─── DESKTOP SCRIPT ─────────────────────────────────────────────────────────
_DESKTOP_SCRIPT = """
// 6. Che Chrome runtime
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {},
    webstore: {}
};

// 7. Che plugins (desktop Chrome có internal plugins)
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5].map(() => ({name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'})),
});

// 8. WebGL - Desktop hay dùng Intel
try {
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter(parameter);
    };
} catch(e) {}

// 9. deviceMemory, hardwareConcurrency cho desktop
Object.defineProperty(navigator, 'deviceMemory', {get: () => [4, 8][Math.floor(Math.random() * 2)]});
Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => [4, 6, 8, 12][Math.floor(Math.random() * 4)]});
"""


# ─── MOBILE SCRIPT BUILDER ──────────────────────────────────────────────────
def _build_mobile_script(device_name: str) -> str:
    """Tạo anti-detect script cho mobile với fingerprint đúng theo thiết bị."""
    fp = _DEVICE_FINGERPRINTS.get(device_name) or _DEVICE_FINGERPRINTS["Mobile fallback"]

    gpu_vendor = fp["gpu_vendor"]
    gpu_renderer = fp["gpu_renderer"]
    cores = fp["cores"]
    ram = fp["ram"]
    platform = fp["platform"]
    has_chrome = "true" if fp["has_chrome"] else "false"
    has_plugins = fp["has_plugins"]

    extra_js = ""

    # Chrome runtime: chỉ inject nếu thiết bị là Android (có Chrome)
    if fp["has_chrome"]:
        extra_js += """
// 6a. Che Chrome runtime (Android Chrome có object này)
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {},
    webstore: {}
};
"""
    else:
        # iOS Safari KHÔNG có window.chrome — xoá nếu tồn tại
        extra_js += """
// 6b. iOS Safari không có window.chrome — đảm bảo undefined
Object.defineProperty(window, 'chrome', {
    get: () => undefined,
    configurable: true,
});
"""

    # Plugins: iOS = 0 plugins, Android = 5 plugins
    if has_plugins:
        extra_js += """
// 7a. Plugins: Android Chrome có vài internal plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5].map(() => ({name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'})),
});
"""
    else:
        extra_js += """
// 7b. iOS Safari không có plugins
Object.defineProperty(navigator, 'plugins', {get: () => [], configurable: true});
"""

    mobile_specific = f"""
// 8. Platform: {platform} (theo thiết bị)
Object.defineProperty(navigator, 'platform', {{get: () => '{platform}', configurable: true}});

// 9. WebGL - GPU đúng: {gpu_vendor} / {gpu_renderer}
try {{
    const getParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {{
        if (parameter === 37445) return '{gpu_vendor}';
        if (parameter === 37446) return '{gpu_renderer}';
        return getParam(parameter);
    }};
}} catch(e) {{}}

// 10. deviceMemory, hardwareConcurrency chuẩn theo thiết bị ({ram}GB, {cores} cores)
Object.defineProperty(navigator, 'deviceMemory', {{get: () => {ram}}});
Object.defineProperty(navigator, 'hardwareConcurrency', {{get: () => {cores}}});

// 11. maxTouchPoints: mobile luôn có touch
Object.defineProperty(navigator, 'maxTouchPoints', {{get: () => 5}});
"""

    return _BASE_SCRIPT + extra_js + mobile_specific


def _build_desktop_script() -> str:
    """Tạo anti-detect script cho desktop (Intel Iris OK)."""
    return _BASE_SCRIPT + _DESKTOP_SCRIPT


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
        if "Desktop" in selected_device:
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
                "Chrome/126.0.0.0 Safari/537.36"
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
        if is_desktop:
            script = _build_desktop_script()
            print(f"   [🛡️] Anti-detect: Desktop (Intel Iris)")
        else:
            script = _build_mobile_script(selected_device)
            print(f"   [🛡️] Anti-detect: Mobile ({selected_device} — {_DEVICE_FINGERPRINTS.get(selected_device, {}).get('gpu_renderer', 'unknown')})")
        await context.add_init_script(script)

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
