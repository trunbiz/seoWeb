# main.py
import asyncio
import config.settings as cfg
from core.browser_manager import BrowserManager
from tests.test_direct_access import run_direct_test 

async def worker(manager, browser, proxy, index):
    """
    Hàm worker đại diện cho 1 luồng (1 tab)
    """
    try:
        print(f"[{index}] Khởi tạo tab với Proxy: {proxy}...")
        
        # Tạo context mới với proxy riêng biệt
        page = await manager.create_context(browser, proxy_info=proxy)
        
        # Chạy bài test
        await run_direct_test(page)
        
        # Đóng page sau khi xong để giải phóng RAM
        await page.close()
        print(f"[{index}] ✅ Hoàn thành.")
        
    except Exception as e:
        print(f"[{index}] ❌ Lỗi: {e}")

async def main():
    manager = BrowserManager()
    browser = await manager.launch_browser()
    
    proxies = cfg.PROXY_LIST
    
    # Nếu danh sách proxy rỗng hoặc ít hơn số lượng muốn chạy, có thể báo lỗi hoặc lặp lại
    if not proxies:
        print("Vui lòng điền proxy vào config/settings.py!")
        await manager.close()
        return

    tasks = []
    
    # Giả sử bạn muốn chạy tối đa 10 tab (hoặc theo số lượng proxy có)
    max_tabs = 10 
    
    print(f"🚀 Đang khởi chạy {min(len(proxies), max_tabs)} luồng đồng thời...")

    for i in range(min(len(proxies), max_tabs)):
        proxy = proxies[i]
        # Tạo task và thêm vào danh sách chờ
        tasks.append(worker(manager, browser, proxy, i+1))
    
    # Chạy tất cả các task cùng lúc
    await asyncio.gather(*tasks)
    
    print("🏁 Tất cả các luồng đã kết thúc.")
    await manager.close()

if __name__ == "__main__":
    asyncio.run(main())