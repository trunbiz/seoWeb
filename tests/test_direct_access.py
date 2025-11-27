# tests/test_direct_access.py
import asyncio
import random
from playwright.async_api import Page
from utils.interactions import human_scroll, click_random_internal_link, random_highlight_text
import config.settings as cfg

async def run_deep_session(page: Page):
    """
    Kịch bản Deep Session:
    Vào trang chủ -> Đọc -> Vào trang con 1 -> Đọc -> (Có thể) Vào trang con 2 -> Thoát
    """
    target_url = cfg.TARGET_URL
    total_time_spent = 0
    
    try:
        print(f"--- [SESSION START] Truy cập: {target_url} ---")
        
        # BƯỚC 1: Truy cập trang đích
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        
        # Thời gian đọc trang đầu (30-50% tổng thời gian)
        t1 = random.randint(20, 40)
        await human_scroll(page, duration=t1)
        total_time_spent += t1
        
        # BƯỚC 2: Click chuyển trang (Deep View Level 1)
        if await click_random_internal_link(page):
            try:
                await page.wait_for_load_state("domcontentloaded")
                print("   [+] Đã vào trang con Level 1.")
                
                # Thời gian đọc trang con
                t2 = random.randint(30, 50)
                await human_scroll(page, duration=t2)
                total_time_spent += t2
                
                # BƯỚC 3: (50% Cơ hội) Click sâu thêm tầng nữa (Level 2)
                if random.choice([True, False]) and total_time_spent < cfg.TEST_DURATION:
                    if await click_random_internal_link(page):
                        await page.wait_for_load_state("domcontentloaded")
                        print("   [+] Đã vào trang con Level 2.")
                        await human_scroll(page, duration=30)
                        
            except Exception as e:
                print(f"   [-] Lỗi load trang con: {e}")
        else:
            print("   [-] Không tìm thấy link để click sâu, tiếp tục đọc trang hiện tại.")
            await human_scroll(page, duration=20)

        print(f"--- [SESSION END] Hoàn thành. Tổng thời gian: ~{total_time_spent}s ---")

    except Exception as e:
        print(f"--- [FAILED] Lỗi Session: {e} ---")