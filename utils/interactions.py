# utils/interactions.py
import asyncio
import random
from playwright.async_api import Page
from utils.mouse_helper import human_move

async def random_sleep(min_s=1.0, max_s=3.0):
    await asyncio.sleep(random.uniform(min_s, max_s))

async def human_scroll(page: Page, duration: int):
    """Cuộn trang kết hợp đọc, rung chuột và bôi đen"""
    print(f"   [*] 📖 Đang đọc & tương tác ({duration}s)...")
    start_time = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start_time < duration:
        # Cuộn xuống
        await page.mouse.wheel(0, random.randint(150, 400))
        
        # Random hành vi phụ
        dice = random.random()
        if dice < 0.15:
            await random_mouse_jitter(page)
        elif dice < 0.25:
            await random_highlight_text(page)
        elif dice < 0.35: # Cuộn ngược lên (xem lại)
            await page.mouse.wheel(0, -random.randint(100, 300))

        await asyncio.sleep(random.uniform(1.5, 4.0))

async def random_mouse_jitter(page: Page):
    """Rung lắc chuột nhẹ"""
    try:
        x, y = random.randint(300, 1000), random.randint(300, 800)
        # Dùng human_move để đến điểm rung
        await human_move(page, x, y)
        for _ in range(random.randint(3, 5)):
            await page.mouse.move(x + random.randint(-10, 10), y + random.randint(-10, 10))
            await asyncio.sleep(0.05)
    except: pass

async def random_highlight_text(page: Page):
    """Bôi đen văn bản"""
    try:
        paragraphs = await page.locator("p, span").all()
        if not paragraphs: return
        
        target = random.choice(paragraphs)
        if await target.is_visible():
            box = await target.bounding_box()
            if box:
                # Dùng human_move để đến điểm bắt đầu
                await human_move(page, box['x'], box['y'])
                await asyncio.sleep(0.3)
                
                await page.mouse.down()
                # Kéo chuột
                await human_move(page, box['x'] + random.randint(50, 200), box['y'] + 10)
                await page.mouse.up()
                
                await asyncio.sleep(1.0)
                # Click ra ngoài để bỏ chọn
                await page.mouse.click(box['x'] - 20, box['y'])
    except: pass

async def click_random_internal_link(page: Page):
    """Click link nội bộ an toàn"""
    try:
        current_url = page.url
        domain_parts = current_url.split("/")
        if len(domain_parts) < 3: return False
        base_domain = domain_parts[2]

        # Lấy link chứa domain hoặc link tương đối
        selector = f"a[href*='{base_domain}'], a[href^='/']"
        links = await page.locator(selector).all()
        
        valid_links = [l for l in links if await l.is_visible()]
        
        if valid_links:
            target = random.choice(valid_links)
            txt = await target.inner_text()
            
            await target.scroll_into_view_if_needed()
            await random_sleep(0.5, 1.0)
            
            box = await target.bounding_box()
            if box:
                # Di chuyển chuột thật đến tâm nút
                center_x = box['x'] + box['width']/2 + random.randint(-5, 5)
                center_y = box['y'] + box['height']/2 + random.randint(-5, 5)
                await human_move(page, center_x, center_y)
                
                # Hiệu ứng hover
                await asyncio.sleep(random.uniform(0.2, 0.5))
                await target.click()
                print(f"   [+] 👆 Click: {txt.strip()[:20]}...")
                return True
        return False
    except Exception:
        return False