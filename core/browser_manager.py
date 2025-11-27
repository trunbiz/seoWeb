# core/browser_manager.py
import os
import asyncio
from playwright.async_api import async_playwright
from fake_useragent import UserAgent
import config.settings as cfg

try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None

class BrowserManager:
    def __init__(self):
        try:
            self.ua = UserAgent()
        except:
            self.ua = None

    async def launch_browser(self):
        self.playwright = await async_playwright().start()
        
        # Lấy danh sách devices từ chính Playwright instance
        self.devices = self.playwright.devices 
        
        args = [
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-sandbox"
        ]
        
        # Lưu ý: Nếu giả lập Mobile, không nên dùng --start-maximized vì nó sẽ phá vỡ viewport điện thoại
        if cfg.DEVICE_NAME != "Desktop":
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

        # --- [LOGIC CHỌN THIẾT BỊ] ---
        device_config = {}
        
        # 1. Nếu chọn Mobile cụ thể (VD: "iPhone 13")
        if cfg.DEVICE_NAME and cfg.DEVICE_NAME != "Desktop" and "Desktop" not in cfg.DEVICE_NAME:
            # Lấy cấu hình chuẩn từ Playwright
            if cfg.DEVICE_NAME in self.devices:
                device_config = self.devices[cfg.DEVICE_NAME]
                print(f"   [📱] Giả lập: {cfg.DEVICE_NAME}")
            else:
                print(f"   [⚠️] Không tìm thấy thiết bị '{cfg.DEVICE_NAME}', dùng Desktop.")
        
        # 2. Nếu là Desktop -> Tự cấu hình như cũ
        else:
            # Random User-Agent máy tính
            user_agent_str = self.ua.random if self.ua else "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
            device_config = {
                "viewport": cfg.VIEWPORT_SIZE, # Lấy từ file config hoặc UI
                "user_agent": user_agent_str,
                "has_touch": False,
                "is_mobile": False,
                "locale": "en-US",
                "timezone_id": "America/New_York"
            }

        # --- MERGE CẤU HÌNH ---
        context_opts = {
            **device_config, # Bung cấu hình thiết bị vào đây
            "ignore_https_errors": True,
            "permissions": ["geolocation"] # Cho phép định vị nếu cần
        }

        # 3. Xử lý Proxy & Timezone (Ghi đè lên device config nếu cần)
        if proxy_info:
            context_opts["proxy"] = {"server": proxy_info}
            if ".vn" in proxy_info or "171." in proxy_info:
                context_opts["locale"] = "vi-VN"
                context_opts["timezone_id"] = "Asia/Ho_Chi_Minh"

        # 4. Load Cookies
        if os.path.exists(state_path):
            context_opts["storage_state"] = state_path

        context = await browser.new_context(**context_opts)

        # --- TIÊM SCRIPT (Giữ nguyên) ---
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            try {
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) return 'Intel Inc.';
                    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                    return getParameter(parameter);
                };
            } catch(e) {}
        """)

        page = await context.new_page()
        if stealth_async: await stealth_async(page)

        # Auto Save
        async def save_state():
            try:
                await context.storage_state(path=state_path)
            except: pass
        context.on("close", lambda: asyncio.create_task(save_state()))
        
        return page

    async def close(self):
        if hasattr(self, 'browser'): await self.browser.close()
        if hasattr(self, 'playwright'): await self.playwright.stop()