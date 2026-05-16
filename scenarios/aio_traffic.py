"""
scenarios/aio_traffic.py — AIO traffic: hoi AI, roi search Google + click target.
"""
import asyncio
import random
from playwright.async_api import Page
from utils.interactions import human_scroll, random_sleep

AIO_PLATFORMS = [
    {"name": "Gemini",     "url": "https://gemini.google.com",    "input_sel": "textarea, [contenteditable='true']"},
    {"name": "ChatGPT",    "url": "https://chatgpt.com",          "input_sel": "textarea, [contenteditable='true']"},
    {"name": "Perplexity", "url": "https://www.perplexity.ai",    "input_sel": "textarea"},
]

QUESTIONS = [
    "nankybeauty.com noi mi quan 2 co tot khong",
    "nankybeauty review noi mi dep",
    "noi mi tu nhien o nankybeauty.com",
]

SITES = ["nankybeauty.com", "topdev.vn/nhan-noi-mi/"]

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
        except:
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
        except:
            pass
    return False

async def run_aio_session(page: Page):
    """Step 1: Hoi AI. Step 2: Search Google + click target."""
    platform = random.choice(AIO_PLATFORMS)
    question = random.choice(QUESTIONS)
    target_url = random.choice(SITES)

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
    try:
        search_q = target_url.replace("https://", "").replace("http://", "").replace("/", " ")
        await page.goto(f"https://www.google.com/search?q={search_q.replace(' ', '+')}",
                       wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Tim link den target site
        target_domain = target_url.replace("https://", "").replace("http://", "").split("/")[0]
        links = await page.locator("a").all()
        clicked = False
        for link in links:
            try:
                href = await link.get_attribute("href")
                if href and target_domain in href.lower():
                    await link.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await link.click()
                    await asyncio.sleep(3)
                    print(f"   [AIO] Da click: {target_domain}")
                    clicked = True
                    break
            except:
                pass

        if not clicked:
            print(f"   [AIO] Khong tim thay link {target_domain} trong kq Google")
            await human_scroll(page, duration=random.randint(10, 15))

    except Exception as e:
        print(f"   [AIO] Step 2 error: {str(e)[:50]}")

    print(f"   [AIO] Session done.")
