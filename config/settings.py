# config/settings.py

# --- 1. CẤU HÌNH CƠ BẢN ---
TARGET_URL = "https://topdev.vn" 
PROXY_LIST = [] 

# --- 2. CẤU HÌNH TRÌNH DUYỆT ---
HEADLESS_MODE = False      
LOAD_IMAGES = True         

VIEWPORT_SIZE = {"width": 1920, "height": 1080} 

# --- 3. CẤU HÌNH GIẢ LẬP THIẾT BỊ ---
DEVICE_NAME = "Desktop" 

# [CẬP NHẬT] Thêm lựa chọn Random
SUPPORTED_DEVICES = [
    "Desktop (Mặc định)",
    "Random (Ngẫu nhiên mọi loại)", # <-- Mới
    "Random Mobile (Chỉ điện thoại)", # <-- Mới
    "iPhone 14 Pro",
    "iPhone 14 Pro Max",
    "iPhone 13 Mini",
    "Pixel 7",
    "Pixel 5",
    "Samsung Galaxy S22",
    "iPad Pro 11"
]

# --- 4. CẤU HÌNH THỜI GIAN ON-SITE ---
DURATION_MIN = 60
DURATION_MAX = 120
TEST_DURATION = 60 

# --- 5. CẤU HÌNH TREO MÁY (LOOP MODE) --- [MỚI]
LOOP_ENABLE = False        # Có chạy lặp lại theo thời gian không?
LOOP_DURATION = 60         # Tổng thời gian treo tool (Phút)

# --- 6. CẤU HÌNH NUÔI NICK ---
WARMUP_ENABLE = False      
WARMUP_YOUTUBE = True      
WARMUP_NEWS = True         
WARMUP_WIKIPEDIA = True    
WARMUP_SHOPPING = True