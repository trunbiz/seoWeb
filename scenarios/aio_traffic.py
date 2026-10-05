"""
scenarios/aio_traffic.py — AIO traffic: hoi AI, roi search Google + click target.
"""
import asyncio
import random
from urllib.parse import quote
from urllib.parse import urlparse
from playwright.async_api import Page
from utils.interactions import human_scroll, random_sleep
import config.settings as cfg
from utils.targets import get_target_url

AIO_PLATFORMS = [
    {"name": "Gemini",     "url": "https://gemini.google.com",    "input_sel": "textarea, [contenteditable='true']"},
    {"name": "ChatGPT",    "url": "https://chatgpt.com",          "input_sel": "textarea, [contenteditable='true']"},
    {"name": "Perplexity", "url": "https://www.perplexity.ai",    "input_sel": "textarea"},
]

async def dismiss_popups(page: Page):
    for sel in [
        "button:has-text('Accept')", "button:has-text('Accept all')",
        "button:has-text('Dong y')", "button:has-text('Cho phep')",
        "button:has-text('Reject')",
    ]:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=500):
                await btn.click()
                await asyncio.sleep(0.5)
        except Exception:
            pass

async def find_and_type(page: Page, text: str) -> bool:
    for sel in ["textarea", "[contenteditable='true']", "input[type='text']"]:
        try:
            box = page.locator(sel).first
            if await box.is_visible(timeout=3000):
                await box.click()
                await asyncio.sleep(1)
                await page.keyboard.type(text, delay=random.randint(40, 80))
                return True
        except Exception:
            pass
    return False

async def run_aio_session(page: Page, stop_event=None, duration=None):
    from utils.captcha import GoogleCaptchaDetected, direct_after_captcha, visit_target_direct
    """Step 1: Hoi AI. Step 2: Search Google + click target."""
    if duration is None:
        duration = cfg.TEST_DURATION
    platform = random.choice(AIO_PLATFORMS)
    target_url = get_target_url().strip()
    domain = urlparse(target_url if "://" in target_url else f"https://{target_url}").netloc
    keyword = random.choice(cfg.SEO_KEYWORDS) if cfg.SEO_KEYWORDS else domain
    question = f"{keyword} {domain} co tot khong"

    print(f"   [AIO] Step 1: {platform['name']} - {question}")

    # Step 1: Hoi AI
    try:
        await page.goto(platform["url"], wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(4)
        await dismiss_popups(page)
        await asyncio.sleep(2)

        typed = await find_and_type(page, question)
        if typed:
            await random_sleep(1, 2)
            await page.keyboard.press("Enter")
            print(f"   [AIO] Dang cho AI tra loi...")
            await asyncio.sleep(random.randint(8, 12))
            await human_scroll(page, duration=random.randint(10, 20))
            print(f"   [AIO] Step 1 done - da hoi AI.")
        else:
            print(f"   [AIO] Khong tim thay input - skip Step 1")
    except Exception as e:
        print(f"   [AIO] Step 1 error: {str(e)[:50]}")

    # Step 2: Search Google + click target
    print(f"   [AIO] Step 2: Search Google -> {target_url}")
    clicked = False
    try:
        # Xay dung search query tu URL cau hinh trong UI.
        search_query = target_url.replace("https://", "").replace("http://", "").replace("/", " ").strip()
        encoded_query = quote(search_query)
        await page.goto(f"https://www.google.com/search?q={encoded_query}",
                       wait_until="domcontentloaded", timeout=30000)
        from utils.captcha import wait_for_verification
        if not await wait_for_verification(page, stop_event):
            return await visit_target_direct(page, duration, stop_event)
        await asyncio.sleep(3)

        # Tim link den target site (dung match chinh xac hon)
        links = await page.locator(f"a[href*='{domain.lower()}']").all()

        for link in links:
            try:
                href = await link.get_attribute("href")
                href_domain = urlparse(href).netloc.lower().lstrip("www.") if href else ""
                target_domain = domain.lower().lstrip("www.")
                if href and (href_domain == target_domain or href_domain.endswith("." + target_domain)):
                    await link.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await link.click()
                    await asyncio.sleep(3)
                    current_domain = urlparse(page.url).netloc.lower().lstrip("www.")
                    target_domain = domain.lower().lstrip("www.")
                    if current_domain == target_domain or current_domain.endswith("." + target_domain):
                        print(f"   [AIO] Da click: {target_url}")
                        clicked = True
                        break
            except Exception:
                pass

        if not clicked:
            print(f"   [AIO] Khong tim thay link {target_url} trong kq Google")
            return await visit_target_direct(page, duration, stop_event, reason="NO SEARCH RESULT")

    except GoogleCaptchaDetected:
        return await direct_after_captcha(page, duration, stop_event)
    except Exception as e:
        print(f"   [AIO] Step 2 error: {str(e)[:50]}")
        return await visit_target_direct(page, duration, stop_event)

    from utils.onsite_interactions import auto_close_popups, rich_on_site_interaction
    await auto_close_popups(page)
    await rich_on_site_interaction(page, keyword, max_pages=3, duration=duration)
    print(f"   [AIO] Session done.")
    return clicked
