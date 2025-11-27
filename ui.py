import customtkinter as ctk
import threading
import asyncio
import sys
import random
import time
import uuid  # Dùng để tạo ID ngẫu nhiên
from tkinter import END

# --- IMPORT CÁC MODULE ---
from core.browser_manager import BrowserManager
from tests.test_direct_access import run_deep_session
import config.settings as cfg

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class RedirectText(object):
    def __init__(self, text_ctrl):
        self.output = text_ctrl
    def write(self, string):
        self.output.insert(END, string)
        self.output.see(END)
    def flush(self): pass

class TrafficBotUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Traffic Bot Ultimate - Auto Loop & Clean Session")
        self.geometry("1250x800")
        self.is_running = False
        self.stop_event = threading.Event()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ================= SIDEBAR =================
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="CONTROL CENTER", font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, padx=20, pady=(30, 20))

        # Nút START/STOP
        self.btn_start = ctk.CTkButton(self.sidebar, text="▶ BẮT ĐẦU TREO MÁY", fg_color="#009900", height=50, font=ctk.CTkFont(size=14, weight="bold"), command=self.start_thread)
        self.btn_start.grid(row=1, column=0, padx=20, pady=(10, 10))
        
        self.btn_stop = ctk.CTkButton(self.sidebar, text="⏹ DỪNG KHẨN CẤP", fg_color="#990000", state="disabled", height=40, command=self.stop_process)
        self.btn_stop.grid(row=2, column=0, padx=20, pady=(0, 20))

        self.lbl_status = ctk.CTkLabel(self.sidebar, text="Trạng thái: Sẵn sàng", text_color="gray")
        self.lbl_status.grid(row=3, column=0, padx=20, pady=10)
        
        # Đồng hồ đếm ngược (Hiển thị thời gian còn lại)
        self.lbl_timer = ctk.CTkLabel(self.sidebar, text="", font=("Consolas", 16, "bold"), text_color="yellow")
        self.lbl_timer.grid(row=4, column=0, padx=20, pady=10)

        # ================= MAIN AREA =================
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # --- TABVIEW ---
        self.tabs = ctk.CTkTabview(self.main_frame, height=450)
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.tab_general = self.tabs.add("Cài Đặt Chung")
        self.tab_loop = self.tabs.add("Cấu Hình Treo Máy") # Tab Mới
        self.tab_browser = self.tabs.add("Thiết Bị & Trình Duyệt")
        self.tab_behavior = self.tabs.add("Hành Vi User")
        self.tab_warmup = self.tabs.add("Nuôi Nick")

        self.setup_tab_general()
        self.setup_tab_loop()      # Setup Tab Mới
        self.setup_tab_browser()
        self.setup_tab_behavior()
        self.setup_tab_warmup()

        # --- LOG AREA ---
        self.log_frame = ctk.CTkFrame(self.main_frame)
        self.log_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(10, 0))
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.log_frame, text="System Logs:", anchor="w", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.txt_log = ctk.CTkTextbox(self.log_frame, font=("Consolas", 11), fg_color="#1a1a1a", text_color="#00ff00")
        self.txt_log.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        sys.stdout = RedirectText(self.txt_log)
        sys.stderr = RedirectText(self.txt_log)

    # ---------------- SETUP TABS ----------------

    def setup_tab_general(self):
        """Tab 1: URL, Proxy, Threads"""
        ctk.CTkLabel(self.tab_general, text="Target URL:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.entry_url = ctk.CTkEntry(self.tab_general, width=450)
        self.entry_url.insert(0, cfg.TARGET_URL)
        self.entry_url.grid(row=1, column=0, sticky="w", padx=10)

        ctk.CTkLabel(self.tab_general, text="Số luồng chạy đồng thời (Threads):").grid(row=2, column=0, sticky="w", padx=10, pady=(15, 5))
        self.slider_threads = ctk.CTkSlider(self.tab_general, from_=1, to=20, number_of_steps=19)
        self.slider_threads.set(5) # Mặc định 5 luồng như bạn yêu cầu
        self.slider_threads.grid(row=3, column=0, sticky="ew", padx=10)
        
        ctk.CTkLabel(self.tab_general, text="Danh sách Proxy (Mỗi dòng 1 cái):").grid(row=0, column=1, sticky="w", padx=20, pady=5)
        self.txt_proxy = ctk.CTkTextbox(self.tab_general, width=300, height=250)
        self.txt_proxy.grid(row=1, column=1, rowspan=4, sticky="nsew", padx=20)
        if cfg.PROXY_LIST: self.txt_proxy.insert("0.0", "\n".join(cfg.PROXY_LIST))

    def setup_tab_loop(self):
        """Tab 2: Cấu hình Treo máy (Loop)"""
        self.chk_loop = ctk.CTkCheckBox(self.tab_loop, text="KÍCH HOẠT CHẾ ĐỘ TREO MÁY (AUTO LOOP)", font=("Arial", 12, "bold"))
        self.chk_loop.grid(row=0, column=0, sticky="w", padx=20, pady=20)
        
        ctk.CTkLabel(self.tab_loop, text="Tổng thời gian treo máy (Phút):").grid(row=1, column=0, sticky="w", padx=40)
        self.entry_loop_time = ctk.CTkEntry(self.tab_loop, width=150, placeholder_text="Ví dụ: 120")
        self.entry_loop_time.insert(0, "120") # Mặc định 120 phút (2 tiếng)
        self.entry_loop_time.grid(row=2, column=0, sticky="w", padx=40, pady=5)
        
        # Tính năng quan trọng: User mới
        self.chk_new_user = ctk.CTkCheckBox(self.tab_loop, text="Luôn là User Mới (Không dùng lại Cookie cũ)")
        self.chk_new_user.select() # Mặc định chọn để sạch traffic
        self.chk_new_user.grid(row=3, column=0, sticky="w", padx=20, pady=20)
        
        ctk.CTkLabel(self.tab_loop, text="* Ghi chú: Khi hết 1 lượt chạy (5 luồng xong), \ntool sẽ tự mở 5 luồng mới cho đến khi hết giờ.").grid(row=4, column=0, sticky="w", padx=20, pady=10)

    def setup_tab_browser(self):
        """Tab 3: Device"""
        ctk.CTkLabel(self.tab_browser, text="Thiết Bị Giả Lập:").grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))
        self.combo_device = ctk.CTkComboBox(self.tab_browser, values=cfg.SUPPORTED_DEVICES, width=250)
        self.combo_device.set("Desktop (Mặc định)")
        self.combo_device.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 20))
        
        self.sw_headless = ctk.CTkSwitch(self.tab_browser, text="Chạy Ngầm (Headless)")
        self.sw_headless.grid(row=2, column=0, sticky="w", padx=20, pady=10)
        self.sw_images = ctk.CTkSwitch(self.tab_browser, text="Tải Hình Ảnh")
        self.sw_images.select()
        self.sw_images.grid(row=3, column=0, sticky="w", padx=20, pady=10)

    def setup_tab_behavior(self):
        """Tab 4: Time On Site"""
        ctk.CTkLabel(self.tab_behavior, text="Thời gian xem trang (Giây):").grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=10)
        
        self.entry_min_time = ctk.CTkEntry(self.tab_behavior, width=80)
        self.entry_min_time.insert(0, str(cfg.DURATION_MIN))
        self.entry_min_time.grid(row=1, column=0, sticky="w", padx=10)
        
        ctk.CTkLabel(self.tab_behavior, text="đến").grid(row=1, column=1, sticky="w")
        
        self.entry_max_time = ctk.CTkEntry(self.tab_behavior, width=80)
        self.entry_max_time.insert(0, str(cfg.DURATION_MAX))
        self.entry_max_time.grid(row=1, column=2, sticky="w", padx=10)

    def setup_tab_warmup(self):
        """Tab 5: Warmup"""
        self.chk_warmup = ctk.CTkCheckBox(self.tab_warmup, text="BẬT NUÔI NICK (WARMUP)")
        self.chk_warmup.grid(row=0, column=0, sticky="w", padx=20, pady=20)
        
        self.chk_ytb = ctk.CTkCheckBox(self.tab_warmup, text="Youtube"); self.chk_ytb.select()
        self.chk_ytb.grid(row=2, column=0, sticky="w", padx=50)
        
        self.chk_news = ctk.CTkCheckBox(self.tab_warmup, text="Đọc Báo"); self.chk_news.select()
        self.chk_news.grid(row=3, column=0, sticky="w", padx=50)
        
        self.chk_wiki = ctk.CTkCheckBox(self.tab_warmup, text="Wikipedia"); self.chk_wiki.select()
        self.chk_wiki.grid(row=4, column=0, sticky="w", padx=50)
        
        self.chk_shop = ctk.CTkCheckBox(self.tab_warmup, text="Shopping"); self.chk_shop.select()
        self.chk_shop.grid(row=5, column=0, sticky="w", padx=50)

    # ---------------- LOGIC CHẠY ----------------

    def start_thread(self):
        if self.is_running: return
        self.is_running = True
        self.stop_event.clear()
        self.update_ui_state(running=True)
        
        # Load Config
        cfg.TARGET_URL = self.entry_url.get()
        proxies = self.txt_proxy.get("0.0", "end").strip().split("\n")
        cfg.PROXY_LIST = [p.strip() for p in proxies if p.strip()]
        
        cfg.HEADLESS_MODE = bool(self.sw_headless.get())
        cfg.LOAD_IMAGES = bool(self.sw_images.get())
        
        dev = self.combo_device.get()
        cfg.DEVICE_NAME = "Desktop" if "Desktop" in dev else dev
        cfg.VIEWPORT_SIZE = {"width": 1920, "height": 1080} if cfg.DEVICE_NAME == "Desktop" else None
        
        try:
            cfg.DURATION_MIN = int(self.entry_min_time.get())
            cfg.DURATION_MAX = int(self.entry_max_time.get())
        except: cfg.DURATION_MIN, cfg.DURATION_MAX = 60, 120

        # Config Warmup
        cfg.WARMUP_ENABLE = bool(self.chk_warmup.get())
        cfg.WARMUP_YOUTUBE = bool(self.chk_ytb.get())
        cfg.WARMUP_NEWS = bool(self.chk_news.get())
        cfg.WARMUP_WIKIPEDIA = bool(self.chk_wiki.get())
        cfg.WARMUP_SHOPPING = bool(self.chk_shop.get())

        # CONFIG LOOP & USER
        cfg.LOOP_ENABLE = bool(self.chk_loop.get())
        try:
            cfg.LOOP_DURATION_MINUTES = int(self.entry_loop_time.get())
        except: cfg.LOOP_DURATION_MINUTES = 60
        cfg.ALWAYS_NEW_USER = bool(self.chk_new_user.get())

        threads = int(self.slider_threads.get())
        
        threading.Thread(target=self.run_async_loop, args=(threads,), daemon=True).start()

    def stop_process(self):
        if not self.is_running: return
        print("\n[🛑] ĐANG DỪNG... (Đợi các luồng hiện tại chạy xong)")
        self.stop_event.set()

    def update_ui_state(self, running):
        if running:
            self.btn_start.configure(state="disabled", text="⏳ ĐANG CHẠY...", fg_color="gray")
            self.btn_stop.configure(state="normal", fg_color="#990000")
            self.lbl_status.configure(text="Trạng thái: Đang chạy...", text_color="#00ff00")
        else:
            self.btn_start.configure(state="normal", text="▶ BẮT ĐẦU TREO MÁY", fg_color="#009900")
            self.btn_stop.configure(state="disabled", fg_color="gray")
            self.lbl_status.configure(text="Trạng thái: Đã dừng", text_color="gray")
            self.lbl_timer.configure(text="")

    def run_async_loop(self, max_tabs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.main_logic(max_tabs))
        loop.close()
        self.is_running = False
        self.update_ui_state(running=False)

    # --- WORKER MỚI ---
    async def worker(self, manager, browser, proxy, idx):
        try:
            if self.stop_event.is_set(): return
            
            # --- LOGIC QUAN TRỌNG: TẠO USER MỚI HAY CŨ ---
            if cfg.ALWAYS_NEW_USER:
                # Thêm UUID ngẫu nhiên để luôn tạo profile mới tinh
                # Ví dụ: 123.45.67.89_a1b2c3d4 -> Luôn là file cookie mới
                unique_suffix = str(uuid.uuid4())[:8]
                p_id = f"{proxy if proxy else 'Local'}_{unique_suffix}"
                user_status = "🆕 New User"
            else:
                # Giữ nguyên ID theo Proxy -> Load lại cookie cũ
                p_id = proxy if proxy else f"Local_Worker_{idx}"
                user_status = "♻️ Returning"

            print(f"[{idx}] 🚀 Mở Tab ({user_status}) | Profile: {p_id}")
            
            page = await manager.create_context(browser, proxy_info=proxy, profile_id=p_id)
            
            # 1. WARMUP
            if cfg.WARMUP_ENABLE:
                modes = []
                if cfg.WARMUP_YOUTUBE: modes.append('youtube')
                if cfg.WARMUP_NEWS: modes.append('news')
                if cfg.WARMUP_WIKIPEDIA: modes.append('wiki')
                if cfg.WARMUP_SHOPPING: modes.append('shopping')
                
                if modes:
                    from scenarios.warmup import run_warmup
                    await run_warmup(page, modes)

            # 2. TARGET
            if not self.stop_event.is_set():
                cfg.TEST_DURATION = random.randint(cfg.DURATION_MIN, cfg.DURATION_MAX)
                await run_deep_session(page)
            
            await page.close()
            print(f"[{idx}] ✅ Xong.")
            
        except Exception as e:
            print(f"[{idx}] ❌ Error: {e}")

    # --- MAIN LOGIC VỚI VÒNG LẶP THỜI GIAN ---
    async def main_logic(self, max_tabs):
        manager = BrowserManager()
        try:
            browser = await manager.launch_browser()
            proxies = cfg.PROXY_LIST if cfg.PROXY_LIST else [None]
            
            # Tính toán thời gian kết thúc
            start_time = time.time()
            loop_minutes = cfg.LOOP_DURATION_MINUTES if cfg.LOOP_ENABLE else 999999
            end_time = start_time + (loop_minutes * 60)
            
            print(f"--- 🕒 BẮT ĐẦU TREO MÁY: {loop_minutes} PHÚT ---")

            while time.time() < end_time and not self.stop_event.is_set():
                # Cập nhật đồng hồ đếm ngược trên UI
                remaining = int(end_time - time.time())
                mins, secs = divmod(remaining, 60)
                self.lbl_timer.configure(text=f"⏳ Còn lại: {mins:02d}:{secs:02d}")
                
                print(f"\n>>> 🏁 BẮT ĐẦU LƯỢT MỚI (Threads: {max_tabs}) <<<")
                
                tasks = []
                for i in range(max_tabs):
                    if self.stop_event.is_set(): break
                    p = proxies[i % len(proxies)]
                    await asyncio.sleep(random.uniform(2, 5)) # Delay mở tab
                    tasks.append(asyncio.create_task(self.worker(manager, browser, p, i+1)))
                
                if tasks:
                    await asyncio.gather(*tasks) # Chờ cả 5 luồng xong hết mới sang lượt sau
                
                if self.stop_event.is_set(): break
                
                # Nếu chưa hết giờ, nghỉ 1 chút rồi lặp lại
                if time.time() < end_time:
                    rest_time = random.randint(5, 10)
                    print(f"\n--- 💤 Nghỉ {rest_time}s trước khi lặp lại ---")
                    await asyncio.sleep(rest_time)

            print("\n[FINISH] 🏁 Đã hết thời gian treo máy!")
            self.lbl_timer.configure(text="✅ HOÀN THÀNH")

        except Exception as e:
            print(f"Critical Error: {e}")
        finally:
            await manager.close()

if __name__ == "__main__":
    app = TrafficBotUI()
    app.mainloop()