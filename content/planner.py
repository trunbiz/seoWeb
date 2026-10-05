"""
content/planner.py — Sinh chi?n l??c Content SEO t?ng th?.

Công c? này giúp t?o ra m?t l?ch trình content c?u trúc, t?i ?u theo keyword,
tăng authority cho thương hiệu — thay vì chỉ dựa vào automation.

Dùng AI (Ollama ho?c DeepSeek) ?? phân tích ngách và ?? xu?t n?i dung.
"""
import json
import os
from datetime import datetime, timedelta

# C?u hình — ?u tiên dùng DeepSeek n?u có
CONTENT_MODEL = "qwen3:30b-a3b"  # ho?c "deepseek-chat"
CONTENT_TIMEOUT = 120

# M?u l?ch content 30 ngày cho ngành làm ?p (n?i mi, u?n mi)
DEFAULT_30D_PLAN = [
    # Tu?n 1: Gi?i thi?u & Giáo d?c
    {"day": 1,  "type": "blog",   "keyword": "nối mi tự nhiên là gì",              "target": "Gi?i thích khái ni?m, ai nên làm"},
    {"day": 2,  "type": "blog",   "keyword": "các lo?i n?i mi ph? bi?n",           "target": "So sánh 5-7 lo?i n?i mi"},
    {"day": 3,  "type": "social", "keyword": "n?i mi ???c bao lâu",                "target": "Infographic v? ?? b?n n?i mi"},
    {"day": 4,  "type": "blog",   "keyword": "n?i mi có h?i mi không",             "target": "Gi?i ?áp lo l?ng th??ng g?p"},
    {"day": 5,  "type": "video",  "keyword": "quy trình n?i mi t?i salon",         "target": "Behind-the-scenes 60s TikTok"},
    {"day": 6,  "type": "blog",   "keyword": "cách ch?n salon n?i mi uy tín",      "target": "Checklist cho khách hàng m?i"},
    {"day": 7,  "type": "review", "keyword": "review dịch vụ nối mi Nanky Beauty", "target": "Tổng hợp cảm nhận khách hàng thật"},

    # Tu?n 2: Chuyên sâu & So sánh
    {"day": 8,  "type": "blog",   "keyword": "n?i mi Hàn Qu?c vs Nh?t B?n",        "target": "So sánh chi ti?t 2 tr??ng phái"},
    {"day": 9,  "type": "blog",   "keyword": "ch?m sóc mi sau khi n?i",            "target": "H??ng d?n ch?m sóc 7 ngày"},
    {"day": 10, "type": "social", "keyword": "tr??c và sau khi n?i mi",            "target": "Before/After gallery"},
    {"day": 11, "type": "blog",   "keyword": "n?i mi giá bao nhiêu",               "target": "B?ng giá chi ti?t + y?u t? ?nh h??ng"},
    {"day": 12, "type": "video",  "keyword": "h??ng d?n t? trang ?? mi t?i nhà",   "target": "Tutorial 90s cho khách"},
    {"day": 13, "type": "blog",   "keyword": "u?n mi là gì có t?t không",          "target": "So sánh u?n mi vs n?i mi"},
    {"day": 14, "type": "review", "keyword": "khách hàng n?i ti?ng dùng d?ch v?",  "target": "Case study: khách hàng th?t"},

    # Tu?n 3: M? r?ng & T?o authority
    {"day": 15, "type": "blog",   "keyword": "dịch vụ làm đẹp mắt tr?n gói",        "target": "Gói combo: mi + mày + m?t"},
    {"day": 16, "type": "blog",   "keyword": "phong cách làm ?p Hàn Qu?c hot 2026","target": "Xu h??ng làm ?p Hàn Qu?c"},
    {"day": 17, "type": "social", "keyword": "học nối mi ở đâu",                   "target": "Giới thiệu khóa học tại Nanky Beauty"},
    {"day": 18, "type": "blog",   "keyword": "d?ch v? n?i mi cho cô dâu",           "target": "Gói c??i tr?n gói"},
    {"day": 19, "type": "blog",   "keyword": "cách nh?n bi?t n?i mi ch?t l??ng",    "target": "H??ng d?n cho ng??i m?i"},
    {"day": 20, "type": "video",  "keyword": "ph?ng v?n chuyên viên n?i mi",        "target": "Expert interview 3-5 phút"},
    {"day": 21, "type": "blog",   "keyword": "dịch vụ làm đẹp tại Nanky Beauty",  "target": "Tổng quan về dịch vụ"},

    # Tu?n 4: T?i ?u chuy?n ??i & Kêu g?i hành ??ng
    {"day": 22, "type": "blog",   "keyword": "??a ch? n?i mi ?n tay ? Sài Gòn",    "target": "Local SEO + Google Maps"},
    {"day": 23, "type": "social", "keyword": "khuy?n mãi n?i mi tháng này",         "target": "Promotion post + link ???t l?ch"},
    {"day": 24, "type": "blog",   "keyword": "các l?u ý khi ?i n?i mi l?n d?u",     "target": "Checklist cho newbie"},
    {"day": 25, "type": "blog",   "keyword": "n?i mi cho m?t m?t mí",              "target": "K? thu?t n?i mi cho t?ng d?ng m?t"},
    {"day": 26, "type": "blog",   "keyword": "câu h?i th??ng g?p v? n?i mi",        "target": "FAQ Schema cho Google"},
    {"day": 27, "type": "video",  "keyword": "khách hàng nói gì về Nanky Beauty", "target": "Testimonial compilation"},
    {"day": 28, "type": "blog",   "keyword": "l?ch s? phát tri?n ngành n?i mi",     "target": "Bài dài t?o authority"},
    {"day": 29, "type": "blog",   "keyword": "so sánh các salon nối mi tại VN",    "target": "So sánh có đối chiếu Nanky Beauty"},
    {"day": 30, "type": "review", "keyword": "t?ng k?t tháng: k?t qu? khách hàng",  "target": "Monthly roundup + CTA booking"},
]

def get_plan_summary():
    """Tr? v? b?ng t?ng k?t l?ch content 30 ngày."""
    blogs = sum(1 for p in DEFAULT_30D_PLAN if p["type"] == "blog")
    videos = sum(1 for p in DEFAULT_30D_PLAN if p["type"] == "video")
    socials = sum(1 for p in DEFAULT_30D_PLAN if p["type"] == "social")
    reviews = sum(1 for p in DEFAULT_30D_PLAN if p["type"] == "review")

    return {
        "total": 30,
        "blogs": blogs,
        "videos": videos,
        "socials": socials,
        "reviews": reviews,
        "cost_estimate": f"??c tính: {blogs}x ~15 gi? vi?t + {videos}x ~2 gi? edit + {socials}x ~1 gi? design"
    }

def print_plan():
    """In l?ch content ra console."""
    print("=" * 80)
    print("  CONTENT STRATEGY — 30 NGÀY CHO NANKY BEAUTY")
    print("  M?c tiêu: Xây d?ng authority t? nhiên, gi?m ph? thu?c automation")
    print("=" * 80)
    print(f"{'Ngày':<6} {'Lo?i':<8} {'Keyword':<35} {'M?c tiêu'}")
    print("-" * 80)
    for item in DEFAULT_30D_PLAN:
        print(f"{item['day']:<6} {item['type']:<8} {item['keyword']:<35} {item['target']}")
    print("-" * 80)
    summary = get_plan_summary()
    print(f"T?ng: {summary['total']} bài | Blog: {summary['blogs']} | Video: {summary['videos']} | Social: {summary['socials']} | Review: {summary['reviews']}")
    print(summary['cost_estimate'])
    print("=" * 80)
