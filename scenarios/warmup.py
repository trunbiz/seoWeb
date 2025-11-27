# scenarios/warmup.py
import asyncio
import random
from playwright.async_api import Page
from utils.interactions import human_scroll, human_move, click_random_internal_link, random_sleep

# ---------------- DATA ----------------
YOUTUBE_KEYWORDS = [
    "nhạc lofi chill", "nhạc tiktok remix 2024", "review iphone 15",
    "highlight bóng đá ngoại hạng anh", "hướng dẫn tập gym",
    "mèo máy doremon", "son tung mtp", "mrbeast vietsub"
]

NEWS_SITES = [
    "https://vnexpress.net", "https://dantri.com.vn", "https://kenh14.vn", "https://24h.com.vn"
]

SHOPPING_SITES = [
    "https://shopee.vn", "https://tiki.vn", "https://www.lazada.vn"
]

# ---------------- HÀM HỖ TRỢ ----------------
async def simulate_typing(page: Page, text: str):
    """Gõ phím như người thật"""
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.15))
    await asyncio.sleep(0.5)

async def handle_youtube_consent(page: Page):
    """Tắt popup cookie nếu có"""
    try:
        # Tìm các nút Accept/Reject phổ biến
        btns = page.locator("button[aria-label='Accept all'], button[aria-label='Reject all'], span:text('I agree'), span:text('Accept all')")
        if await btns.first.is_visible():
            await btns.first.click()
            await asyncio.sleep(2)
    except: pass

# ---------------- KỊCH BẢN 1: YOUTUBE (FIXED FALLBACK) ----------------
async def warmup_youtube(page: Page):
    keyword = random.choice(YOUTUBE_KEYWORDS)
    print(f"   [🔥 Warmup] YouTube: '{keyword}'")
    
    try:
        await page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=60000)
        await random_sleep(3, 5)
        await handle_youtube_consent(page)

        # BIẾN CỜ: Kiểm tra xem đã vào xem video được chưa
        has_watched = False 

        # --- PHA 1: CỐ GẮNG SEARCH ---
        try:
            # Tìm nút search (hỗ trợ cả Mobile & Desktop)
            search_btn = page.locator("button[aria-label='Search'], #search-icon-legacy").first
            search_input = page.locator("input#search, input[name='search_query']").first

            # Nếu input ẩn (Mobile), click nút search trước
            if not await search_input.is_visible() and await search_btn.is_visible():
                await search_btn.click()
                await asyncio.sleep(1)

            if await search_input.is_visible():
                await search_input.click()
                await simulate_typing(page, keyword)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(3000) # Chờ load kết quả
                
                # Chọn video từ kết quả
                videos = await page.locator("ytd-video-renderer, ytm-video-with-context-renderer").all()
                if videos:
                    target = videos[random.randint(0, min(len(videos)-1, 3))]
                    await target.scroll_into_view_if_needed()
                    await asyncio.sleep(1)
                    await target.click(force=True)
                    has_watched = True
                    print("   [▶️] Đã click video từ Search.")
        except Exception as e:
            print(f"   [⚠️] Lỗi Search YouTube: {e}. Chuyển sang xem Trang chủ.")

        # --- PHA 2: FALLBACK (NẾU SEARCH THẤT BẠI) ---
        if not has_watched:
            print("   [...fallback...] Click video ngẫu nhiên trên Trang chủ.")
            try:
                # Quay về trang chủ nếu đang lỡ dở
                if "results" in page.url:
                    await page.goto("https://www.youtube.com")
                    await asyncio.sleep(2)
                
                # Chọn video trang chủ (Rich Item)
                home_videos = await page.locator("ytd-rich-item-renderer, ytm-rich-item-renderer").all()
                if home_videos:
                    # Chọn video thứ 2-4 (tránh quảng cáo đầu)
                    target = home_videos[random.randint(0, min(len(home_videos)-1, 4))]
                    await target.scroll_into_view_if_needed()
                    await target.click(force=True)
                    has_watched = True
            except Exception as e:
                print(f"   [❌] Lỗi Fallback YouTube: {e}")

        # --- PHA 3: XEM VIDEO (WATCH TIME) ---
        if has_watched:
            watch_time = random.randint(50, 90)
            print(f"   [👀] Đang xem video trong {watch_time}s...")
            
            start = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start < watch_time:
                # Hành vi ngẫu nhiên khi xem
                dice = random.random()
                if dice < 0.2: await human_move(page, random.randint(100, 500), random.randint(100, 500))
                elif dice < 0.3: # Cuộn xem comment
                    await page.mouse.wheel(0, 400)
                    await asyncio.sleep(2)
                    await page.mouse.wheel(0, -400)
                await asyncio.sleep(5)
        else:
            # Nếu lỗi toàn tập, vẫn chờ 10s để không thoát quá nhanh
            print("   [⏳] Không xem được video, chờ 10s...")
            await asyncio.sleep(10)

    except Exception as e:
        print(f"   [❌] Lỗi YouTube Critical: {e}")

# ---------------- KỊCH BẢN 2: WIKIPEDIA (TRUST CAO) ----------------
async def warmup_wikipedia(page: Page):
    print("   [🔥 Warmup] Đọc Wikipedia (Học thuật)...")
    try:
        # Vào trang bài viết ngẫu nhiên
        await page.goto("https://vi.wikipedia.org/wiki/%C4%90%E1%BA%B7c_bi%E1%BB%87t:Ng%E1%BA%ABu_nhi%C3%AAn", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # Đọc bài (40-60s)
        await human_scroll(page, duration=random.randint(40, 60))
        
        # Click vào 1 thuật ngữ trong bài để đọc tiếp
        if await click_random_internal_link(page):
            await page.wait_for_load_state("domcontentloaded")
            await human_scroll(page, duration=30)
            
    except Exception as e:
        print(f"   [-] Lỗi Wiki: {e}")

# ---------------- KỊCH BẢN 3: SHOPPING (SHOPEE/TIKI) ----------------
async def warmup_shopping(page: Page):
    site = random.choice(SHOPPING_SITES)
    print(f"   [🔥 Warmup] Lướt sàn TMĐT: {site}")
    try:
        await page.goto(site, wait_until="domcontentloaded", timeout=60000)
        await human_scroll(page, duration=random.randint(15, 25))
        
        # Tìm và click sản phẩm (thường là thẻ a chứa hình ảnh)
        # Selector chung cho Shopee/Tiki
        products = await page.locator("a[href*='sp'], a[href*='product'], div[data-view-id] a").all()
        
        # Lọc sản phẩm hiển thị được
        valid_products = [p for p in products[:20] if await p.is_visible()]
        
        if valid_products:
            target = random.choice(valid_products)
            await target.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            print("   [🛒] Xem chi tiết sản phẩm...")
            await target.click()
            
            # Giả vờ xem giá, xem ảnh
            await page.wait_for_load_state("domcontentloaded")
            await human_scroll(page, duration=random.randint(30, 50))
    except Exception as e:
        print(f"   [-] Lỗi Shopping: {e}")

# ---------------- KỊCH BẢN 4: ĐỌC BÁO (CŨ) ----------------
async def warmup_news(page: Page):
    site = random.choice(NEWS_SITES)
    print(f"   [🔥 Warmup] Đọc báo: {site}")
    try:
        await page.goto(site, wait_until="domcontentloaded")
        await human_scroll(page, duration=20)
        if await click_random_internal_link(page):
            await human_scroll(page, duration=40)
    except: pass

# ---------------- MAIN WARMUP ----------------
async def run_warmup(page: Page, enabled_modes: list):
    """
    enabled_modes: list các mode được chọn từ UI ['youtube', 'news', 'wiki', 'shopping']
    """
    if not enabled_modes: return

    print("--- [⏳ WARMUP START] ---")
    
    # Chọn ngẫu nhiên 1 mode trong các mode được bật
    mode = random.choice(enabled_modes)
    
    if mode == 'youtube': await warmup_youtube(page)
    elif mode == 'wiki': await warmup_wikipedia(page)
    elif mode == 'shopping': await warmup_shopping(page)
    elif mode == 'news': await warmup_news(page)
        
    chill = random.randint(5, 8)
    print(f"--- [⏳ WARMUP DONE] Nghỉ {chill}s ---")
    await asyncio.sleep(chill)