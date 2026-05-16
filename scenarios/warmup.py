"""
scenarios/warmup.py — Nâng c?p: ch?y nhi?u mode, thêm Facebook, TikTok, cá nhân hóa theo target.
"""
import asyncio
import random
from playwright.async_api import Page
from utils.interactions import human_scroll, human_move, click_random_internal_link, random_sleep

# ----- DATA -----
YOUTUBE_KEYWORDS = [
    "nh?c lofi chill", "nh?c tiktok remix 2024", "review iphone 15",
    "highlight bóng ?á ngo?i h?ng anh", "h??ng d?n t?p gym",
    "mèo máy doremon", "son tung mtp", "mrbeast vietsub",
    "làm ?p t?i nhà", "n?i mi t? nhiên", "ch?m sóc da m?t",
    "review m? ph?m Hàn Qu?c", "h??ng d?n make-up co b?n"
]

NEWS_SITES = [
    "https://vnexpress.net", "https://dantri.com.vn",
    "https://kenh14.vn", "https://24h.com.vn",
    "https://phunuvietnam.vn", "https://ella.vn"
]

SHOPPING_SITES = [
    "https://shopee.vn", "https://tiki.vn", "https://www.lazada.vn"
]

SOCIAL_SITES = [
    ("https://facebook.com", "Facebook"),
    ("https://www.instagram.com", "Instagram"),
]


async def simulate_typing(page: Page, text: str):
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.15))
    await asyncio.sleep(0.5)


async def handle_consent(page: Page):
    for sel in [
        "button[aria-label*='Accept']", "button[aria-label*='Accept all']",
        "button:has-text('Accept')", "button:has-text('Cho phép')",
        "button:has-text('Dong y')", "[aria-label*='Close']", "button:has-text('T?t c?')",
    ]:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=1000):
                await btn.click()
                await asyncio.sleep(1)
        except: pass


# ----- WARMUP 1: YouTube (tìm video liên quan ??n target n?u có keyword) -----
async def warmup_youtube(page: Page):
    keyword = random.choice(YOUTUBE_KEYWORDS)
    print(f"   [Warmup] YouTube: '{keyword}'")
    try:
        await page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=60000)
        await random_sleep(3, 5)
        await handle_consent(page)

        search_btn = page.locator("button[aria-label='Search'], #search-icon-legacy").first
        search_input = page.locator("input#search, input[name='search_query']").first

        if not await search_input.is_visible() and await search_btn.is_visible():
            await search_btn.click()
            await asyncio.sleep(1)

        if await search_input.is_visible():
            await search_input.click()
            await simulate_typing(page, keyword)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(3000)

            videos = await page.locator("ytd-video-renderer, ytm-video-with-context-renderer").all()
            if videos:
                target = videos[random.randint(0, min(len(videos)-1, 2))]
                await target.scroll_into_view_if_needed()
                await target.click(force=True)
                watch_time = random.randint(15, 30)
                print(f"   [YouTube] Xem {watch_time}s...")
                start = asyncio.get_event_loop().time()
                while asyncio.get_event_loop().time() - start < watch_time:
                    await asyncio.sleep(5)
    except Exception as e:
        print(f"   [-] YouTube: {e}")
        await asyncio.sleep(10)


# ----- WARMUP 2: Wikipedia -----
async def warmup_wikipedia(page: Page):
    print("   [Warmup] Wikipedia")
    try:
        await page.goto("https://vi.wikipedia.org", wait_until="domcontentloaded")
        await random_sleep(2, 4)
        await human_scroll(page, duration=random.randint(15, 25))
        if await click_random_internal_link(page):
            await page.wait_for_load_state("domcontentloaded")
            await human_scroll(page, duration=15)
    except: pass


# ----- WARMUP 3: Shopping -----
async def warmup_shopping(page: Page):
    site = random.choice(SHOPPING_SITES)
    print(f"   [Warmup] Shopping: {site}")
    try:
        await page.goto(site, wait_until="domcontentloaded", timeout=60000)
        await human_scroll(page, duration=random.randint(10, 15))
        products = await page.locator("a[href*='sp'], a[href*='product'], div[data-view-id] a").all()
        valid = [p for p in products[:20] if await p.is_visible()]
        if valid:
            target = random.choice(valid)
            await target.scroll_into_view_if_needed()
            await target.click()
            await page.wait_for_load_state("domcontentloaded")
            await human_scroll(page, duration=random.randint(15, 25))
    except: pass


# ----- WARMUP 4: News -----
async def warmup_news(page: Page):
    site = random.choice(NEWS_SITES)
    print(f"   [Warmup] Doc bao: {site}")
    try:
        await page.goto(site, wait_until="domcontentloaded")
        await human_scroll(page, duration=12)
        if await click_random_internal_link(page):
            await human_scroll(page, duration=18)
    except: pass


# ----- WARMUP 5: Facebook / Instagram -----
async def warmup_social(page: Page, url: str, name: str):
    print(f"   [Warmup] {name}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await random_sleep(3, 6)
        await handle_consent(page)
        await human_scroll(page, duration=random.randint(10, 18))
    except Exception as e:
        print(f"   [-] {name}: {e}")
        await asyncio.sleep(5)


# ----- MAIN: ch?y nhi?u mode -----
async def run_warmup(page: Page, enabled_modes: list):
    """
    enabled_modes: list t? UI ['youtube', 'news', 'wiki', 'shopping', 'facebook', 'instagram']
    N�.c p: ch?y 2-3 mode ng?u nhi�n thay v� ch? 1.
    """
    if not enabled_modes:
        return

    print("--- [WARMUP START] ---")

    # Th�m Facebook & Instagram n?u ???c b?t
    extra_modes = []
    if "facebook" in enabled_modes:
        extra_modes.append("facebook")
    if "instagram" in enabled_modes:
        extra_modes.append("instagram")

    base_modes = [m for m in enabled_modes if m not in ("facebook", "instagram")]
    if not base_modes:
        base_modes = ["youtube", "news"]

    # Quick warmup: chi 1-2 mode (truoc day 2-3 gay cham)
    count = min(random.randint(1, 2), len(base_modes))
    selected = random.sample(base_modes, count)

    # Th�m social n?u ???c b?t
    if extra_modes and random.random() < 0.5:
        selected.append(random.choice(extra_modes))

    random.shuffle(selected)

    for mode in selected:
        if mode == 'youtube':     await warmup_youtube(page)
        elif mode == 'wiki':      await warmup_wikipedia(page)
        elif mode == 'shopping':  await warmup_shopping(page)
        elif mode == 'news':      await warmup_news(page)
        elif mode == 'facebook':  await warmup_social(page, *SOCIAL_SITES[0])
        elif mode == 'instagram': await warmup_social(page, *SOCIAL_SITES[1])

        # Ngh? gi?a c�c mode
        await asyncio.sleep(random.randint(3, 6))

    print("--- [WARMUP DONE] ---")
