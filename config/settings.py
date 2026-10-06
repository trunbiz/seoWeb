# config/settings.py — C?u hình SEO toàn di?n

# ────────────────────────────────────────────────────────────────────────────
# PH?N A: CHI?N L??C N?I DUNG (80%)
# ────────────────────────────────────────────────────────────────────────────

# M?c tiêu content hàng tháng
CONTENT_GOAL_MONTHLY = 30          # 30 bài/tháng: blog, video, social, review
CONTENT_FOCUS = "Công cụ AI tìm kiếm khách hàng"          # Ngách chính
TARGET_URL = "https://maxmorus.com/"   # Website m?c tiêu
TARGET_URLS = [TARGET_URL]           # Website chính, rồi các website bổ sung.

APP_NAME = "ZizaSeo"
APP_VERSION = "1.0.0"

# AI Content Generation
CONTENT_MODEL = "qwen3:30b-a3b"    # Model cho sinh content (ho?c "deepseek-chat")

# ────────────────────────────────────────────────────────────────────────────
# PH?N B: CHI?N L??C BACKLINK (D?I V?I AUTOMATION)
# ────────────────────────────────────────────────────────────────────────────

BACKLINK_GOAL_MONTHLY = 20         # 20 backlink/tháng
BACKLINK_MIN_DA = 20               # Minimum Domain Authority

# ────────────────────────────────────────────────────────────────────────────
# PH?N C: T?I ?U K? THU?T & AUTOMATION (20%)
# ────────────────────────────────────────────────────────────────────────────

# Proxy
PROXY_LIST = []

# Browser
HEADLESS_MODE = False
# "direct": bỏ Google khi gặp CAPTCHA; "manual": chờ xác minh thủ công.
CAPTCHA_ACTION = "direct"
# Chỉ dùng cho CAPTCHA_ACTION = "manual".
CAPTCHA_WAIT_SECONDS = 180
CAPTCHA_COOLDOWN_SECONDS = 60
# Google lỗi/không có kết quả thì vẫn truy cập TARGET_URL trực tiếp.
TARGET_NAVIGATION_ATTEMPTS = 3
TARGET_NAVIGATION_TIMEOUT_MS = 60000
LOAD_IMAGES = True
VIEWPORT_SIZE = {"width": 1920, "height": 1080}

# Device — H? tr? mobile emulation
# M?c d?nh "Random Mobile 70" = 70% mobile, 30% desktop
DEVICE_NAME = "Random Mobile 70 (70% mobile, 30% desktop)"
SUPPORTED_DEVICES = [
    "Desktop (Mặc định)",
    "Random (Ngẫu nhiên mọi loại)",
    "Random Mobile (Chỉ điện thoại)",
    "Random Mobile 70 (70% mobile, 30% desktop)",
    "iPhone 14 Pro", "iPhone 14 Pro Max", "iPhone 13 Mini",
    "Pixel 7", "Pixel 5", "Samsung Galaxy S22",
    "iPad Pro 11",
]

# Android Emulator (ADB) — t?t m?c d?nh, b?t n?u có ?i?n tho?i ?o
ANDROID_EMULATOR_ENABLE = False
ANDROID_EMULATOR_PORT = 5554  # Port m?c d?nh c?a Android Emulator

# Th?i gian on-site (gi?i h?n ?? tránh pattern b?t th??ng)
DURATION_MIN = 45                  # Gi?m xu?ng 45s ?? t? nhiên h?n
DURATION_MAX = 180                 # T?ng lên 180s ?? có phân tán
TEST_DURATION = 60

# Gi?i h?n t?n su?t — TRÁNH B? GOOGLE PHÁT HI?N
MAX_SESSIONS_PER_DAY = 250          # T?i ?a 25 session/ngày (không ph?i 100+)
MIN_INTERVAL_BETWEEN_SESSIONS = 300 # 5 phút giữa 2 session của cùng một worker

# Loop (ch? b?t khi c?n)
LOOP_ENABLE = True
# Chạy vô thời hạn, không nghỉ giữa phiên và không áp dụng hạn mức phiên/ngày.
# Chỉ có hiệu lực khi AUTO LOOP bật; nhấn Dừng để kết thúc.
LOOP_CONTINUOUS = True
LOOP_DURATION_MINUTES = 60
ALWAYS_NEW_USER = True

# Warm-up
WARMUP_ENABLE = True
WARMUP_YOUTUBE = True
WARMUP_NEWS = True
WARMUP_WIKIPEDIA = True
WARMUP_SHOPPING = True
WARMUP_FACEBOOK = True
WARMUP_INSTAGRAM = True

# Traffic — t?i ?u t? nhiên, tránh phát hi?n
TRAFFIC_MODE = "search"  # "direct" | "search" | "aio" | "mix"

# Stagger: m?i lu?ng cách nhau 5-20s thay vì kh?i ??ng ?ng lo?t
THREAD_STAGGER_MIN = 5        # Giây t?i thi?u gi?a các lu?ng khi kh?i ??ng
THREAD_STAGGER_MAX = 25

# Ngh? ng?u nhiên gi?a các session trong cùng 1 lu?ng
REST_BETWEEN_SESSIONS_MIN = 10   # Giây
REST_BETWEEN_SESSIONS_MAX = 45

# Gi? l?p gi? cao ?i?m (peak hours)
PEAK_HOURS_ENABLE = True          # Ch?y nhi?u h?n vào gi? cao ?i?m
PEAK_HOURS = [(9, 11), (14, 16), (19, 22)]  # Khung gi? VN
SEO_KEYWORDS = [
                 "AI tìm lead từ Facebook Group",
                 "AI tìm khách hàng từ Facebook Group",
                 "công cụ AI tìm lead Facebook",
                 "phần mềm tìm lead Facebook Group",
                 "tìm lead Facebook bằng AI",
                 "AI lọc lead Facebook Group",
                 "tool AI săn lead Facebook",
                 "tự động hóa tìm lead Facebook",
                 "Max Morus AI",
                 "cách tìm khách hàng tiềm năng từ Facebook Group"
               ]

# AI Engine
import os

# Chỉ chọn MỘT provider: "gemini", "aibox", "maxmorus" hoặc "local".
# Các cấu hình/key bên dưới chỉ được dùng khi chọn provider tương ứng.
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()
AI_FALLBACK_LOCAL = os.getenv("AI_FALLBACK_LOCAL", "true").strip().lower() in ("true", "1", "yes")

# AI Box: endpoint chat completions đầy đủ; không lưu key trong source.
AIBOX_API_KEY = os.getenv("AIBOX_API_KEY", "")
AIBOX_API_URL = os.getenv("AIBOX_API_URL", "https://api.ai-box.vn/v1/chat/completions")
AIBOX_MODEL = os.getenv("AIBOX_MODEL", "deepseek-v4.1-flash")

# MaxMorus: OpenAI-compatible chat completions.
MAXMORUS_API_KEY = os.getenv("MAXMORUS_API_KEY", "")
MAXMORUS_API_URL = os.getenv("MAXMORUS_API_URL", "https://ai.maxmorus.com/v1/chat/completions")
MAXMORUS_MODEL = os.getenv("MAXMORUS_MODEL", "cl/deepseek/deepseek-v4.1-flash")

# Gemini API - khong ghi API key truc tiep vao source khi dua code len Git.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta"

# Ollama duoc giu lai de kiem tra model local tu UI.
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:30b-a3b"

# Hành vi nâng cao (gi?m thi?u r?i ro)
POGO_STICK_ENABLE = False          # T?T pogo-stick — nguy c? cao
POGO_STICK_MAX = 0
WARMUP_SEARCH_ENABLE = True        # B?T warmup search — traffic t? search
KEYWORD_VARIATION_ENABLE = True     # B?T keyword variation
THIRD_PAGE_ENABLE = False           # T?T third page — d? b? phát hi?n
THIRD_PAGE_CHANCE = 0
