"""Leave blocked Google search or optionally wait for manual verification."""

import asyncio
import config.settings as cfg
from utils.targets import get_target_url
from urllib.parse import urlparse
from playwright.async_api import Error as PlaywrightError


class GoogleCaptchaDetected(Exception):
    """Signal the caller to leave Google and visit the configured target."""


async def direct_after_captcha(page, duration=None, stop_event=None):
    return await visit_target_direct(page, duration, stop_event, reason="CAPTCHA")


async def visit_target_direct(page, duration=None, stop_event=None, reason="SEARCH FAILED"):
    if page.is_closed() or (stop_event is not None and stop_event.is_set()):
        return False
    _log(f"   [{reason} -> DIRECT] Bỏ tìm kiếm Google, truy cập trực tiếp website đích.")
    try:
        from utils.onsite_interactions import auto_close_popups, rich_on_site_interaction
        target = get_target_url().strip()
        attempts = max(1, cfg.TARGET_NAVIGATION_ATTEMPTS)
        for attempt in range(1, attempts + 1):
            if page.is_closed() or (stop_event is not None and stop_event.is_set()):
                return False
            try:
                response = await page.goto(target, referer="", wait_until="domcontentloaded",
                                           timeout=cfg.TARGET_NAVIGATION_TIMEOUT_MS)
                break
            except (PlaywrightError, OSError) as exc:
                _log(f"   [DIRECT] Lần {attempt}/{attempts} không tải được website đích: {exc}")
                if attempt == attempts:
                    return False
                await asyncio.sleep(1)
        if stop_event is not None and stop_event.is_set():
            return False
        expected = (urlparse(target).hostname or "").lower().removeprefix("www.")
        actual = (urlparse(page.url).hostname or "").lower().removeprefix("www.")
        if not expected or not (actual == expected or actual.endswith("." + expected)):
            _log("   [DIRECT] Điều hướng sai website đích, phiên thất bại.")
            return False
        if response is not None and response.status >= 400:
            _log(f"   [DIRECT] Website đích trả HTTP {response.status}, phiên thất bại.")
            return False
        if await is_captcha(page):
            _log("   [DIRECT] Website đích cũng yêu cầu CAPTCHA, bỏ phiên này.")
            return False
        await auto_close_popups(page)
        topic = cfg.SEO_KEYWORDS[0] if cfg.SEO_KEYWORDS else ""
        await rich_on_site_interaction(page, topic, max_pages=2, duration=duration)
        _log("   [DIRECT] Hoàn thành truy cập trực tiếp; không phải lượt từ Google.")
        return True
    except Exception as exc:
        _log(f"   [DIRECT] Truy cập thất bại: {exc}")
        return False


def _log(message):
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", errors="replace").decode("ascii"))


async def is_captcha(page):
    if any(token in page.url.lower() for token in ("/sorry/", "sorry/index", "recaptcha", "captcha")):
        return True
    for selector in (
        "iframe[src*='recaptcha']", "div[class*='g-recaptcha']",
        "div[class*='captcha']", "#captcha", "[aria-label*='captcha']",
    ):
        try:
            if await page.locator(selector).first.is_visible(timeout=500):
                return True
        except Exception:
            continue
    return False


async def wait_for_verification(page, stop_event=None):
    """True when unblocked; False after timeout, closed tab or stop request."""
    def stopped():
        return stop_event is not None and stop_event.is_set()

    if stopped() or page.is_closed():
        return False
    if not await is_captcha(page):
        return True
    if cfg.CAPTCHA_ACTION == "direct":
        raise GoogleCaptchaDetected()
    timeout = max(0, cfg.CAPTCHA_WAIT_SECONDS)
    if cfg.HEADLESS_MODE:
        _log("   [CAPTCHA] Trình duyệt đang ẩn. Tắt Headless để xác minh thủ công.")
    elif timeout:
        _log(f"   [CAPTCHA] Chờ bạn xác minh trong cửa sổ trình duyệt (tối đa {timeout}s).")
        try:
            await page.bring_to_front()
        except Exception:
            pass
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            if stopped() or page.is_closed():
                return False
            if not await is_captcha(page):
                _log("   [CAPTCHA] Đã xác minh, tiếp tục phiên hiện tại.")
                return True
            await asyncio.sleep(min(1, max(0, deadline - asyncio.get_running_loop().time())))
    if stopped() or page.is_closed():
        return False
    cooldown = max(0, cfg.CAPTCHA_COOLDOWN_SECONDS)
    _log(f"   [CAPTCHA] Chưa xác minh. Nghỉ {cooldown}s rồi kết thúc phiên không thành công.")
    deadline = asyncio.get_running_loop().time() + cooldown
    while asyncio.get_running_loop().time() < deadline:
        if stopped() or page.is_closed():
            break
        await asyncio.sleep(min(1, max(0, deadline - asyncio.get_running_loop().time())))
    return False
