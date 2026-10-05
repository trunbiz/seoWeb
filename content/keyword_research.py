"""
content/keyword_research.py — Research t? khóa cho content plan.

Phân tích keyword theo:
- Volume (l??ng tìm ki?m)
- Difficulty (?? c?nh tranh)
- Intent (search intent)
- G?i ý content d?a trên t? khóa
"""
import json
import random

# M?u d? li?u keyword cho ngành làm ?p m?t
SAMPLE_KEYWORDS = [
    # Head terms (volume cao, c?nh tranh cao)
    {"keyword": "n?i mi",              "volume": 14800, "difficulty": 72, "intent": "commercial"},
    {"keyword": "n?i mi ? Sài Gòn",    "volume": 9900,  "difficulty": 65, "intent": "commercial"},
    {"keyword": "n?i mi ? ?u",          "volume": 8100,  "difficulty": 58, "intent": "commercial"},

    # Body terms (volume TB, intent cao)
    {"keyword": "nối mi tự nhiên giá bao nhiêu", "volume": 3200, "difficulty": 45, "intent": "transactional"},
    {"keyword": "n?i mi Hàn Qu?c",               "volume": 2900, "difficulty": 48, "intent": "commercial"},
    {"keyword": "uốn mi ở đâu đẹp",                "volume": 2400, "difficulty": 35, "intent": "commercial"},
    {"keyword": "n?i mi cho cô dâu",             "volume": 1800, "difficulty": 30, "intent": "transactional"},
    {"keyword": "cách ch?m sóc mi n?i",          "volume": 1600, "difficulty": 28, "intent": "informational"},
    {"keyword": "n?i mi ???c bao lâu",           "volume": 2200, "difficulty": 32, "intent": "informational"},
    {"keyword": "review nối mi Nanky Beauty",    "volume": 890,  "difficulty": 12, "intent": "commercial"},

    # Long-tail (volume th?p, intent r?t cao)
    {"keyword": "nối mi tự nhiên không h? mi t?i salon qu?n 1", "volume": 420, "difficulty": 8, "intent": "transactional"},
    {"keyword": "??a ch? n?i mi ?n tay g?n ??y",               "volume": 380, "difficulty": 10, "intent": "commercial"},
    {"keyword": "n?i mi cho ng??i m?t m?t mí 1 mí",            "volume": 320, "difficulty": 15, "intent": "informational"},
    {"keyword": "cách bi?t n?i mi chu?n hay không chu?n",      "volume": 280, "difficulty": 10, "intent": "informational"},
]

# T? khóa d?nh h??ng theo funnel (ph?u chuy?n ??i)
FUNNEL_KEYWORDS = {
    "TOFU (Nh?n th?c)": [
        "n?i mi là gì", "nối mi tự nhiên là gì", "n?i mi có t?t không",
        "các lo?i n?i mi", "n?i mi Hàn Qu?c vs Nh?t B?n"
    ],
    "MOFU (Cân nh?c)": [
        "n?i mi giá bao nhiêu", "n?i mi ? ?u t?t", "n?i mi ???c bao lâu",
        "review n?i mi", "cách ch?n salon n?i mi"
    ],
    "BOFU (Quy?t ??nh)": [
        "đặt lịch nối mi", "nối mi tại Nanky Beauty", "khuyến mãi nối mi",
        "n?i mi giá r? ? Sài Gòn", "d?ch v? n?i mi t?i nhà"
    ],
}


def get_keyword_opportunities(min_volume=300, max_difficulty=50):
    """L?y keyword có c? h?i t?t: volume khá + khó v?a ph?i."""
    opportunities = [k for k in SAMPLE_KEYWORDS
                     if k["volume"] >= min_volume and k["difficulty"] <= max_difficulty]
    opportunities.sort(key=lambda x: -x["volume"])
    return opportunities


def print_keyword_report():
    """In báo cáo keyword ra console."""
    print("=" * 80)
    print("  KEYWORD RESEARCH REPORT — NANKY BEAUTY")
    print("  Ngành: N?i mi, U?n mi, Làm ?p m?t")
    print("=" * 80)

    print(f"\n{'Keyword':<40} {'Volume':<10} {'Khó':<6} {'Intent':<15}")
    print("-" * 80)
    for kw in sorted(SAMPLE_KEYWORDS, key=lambda x: -x["volume"]):
        vol_str = f"{kw['volume']:,}"
        print(f"{kw['keyword']:<40} {vol_str:<10} {kw['difficulty']:<6} {kw['intent']:<15}")

    print(f"\n--- C? h?i t?t (Volume >= 500, Khó <= 50) ---")
    for kw in sorted(get_keyword_opportunities(500, 50), key=lambda x: -x["volume"]):
        vol_str = f"{kw['volume']:,}"
        print(f"  + {kw['keyword']:<38} {vol_str:<10} {kw['difficulty']}/100")

    print(f"\n--- Ph?u Content theo Funnel ---")
    for stage, kws in FUNNEL_KEYWORDS.items():
        print(f"  [{stage}]")
        for kw in kws[:3]:
            print(f"    - {kw}")
    print("=" * 80)
