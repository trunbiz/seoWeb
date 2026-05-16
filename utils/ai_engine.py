# utils/ai_engine.py
"""
Mô phỏng AI engine — tạo personas, hành vi tìm kiếm và keyword variation.
Không cần LLM thật, chỉ cần random có chủ ý theo luật.
"""

import random
from typing import Any

# ─── type alias ──────────────────────────────────────────────────────────────
PersonaConfig = dict[str, Any]

# ─── data ────────────────────────────────────────────────────────────────────

_MOODS = ["hurried", "curious", "relaxed"]
_GENDERS = ["male", "female"]

# Mỗi mood → khoảng age đặc trưng
_AGE_RANGES = {
    "hurried": (22, 35),
    "curious": (18, 30),
    "relaxed": (28, 55),
}

# (type_delay_ms, typo_chance, read_speed_ms)
_PERSONA_PARAMS = {
    "hurried": {"type_delay_ms": (40, 80), "typo_chance": (0.06, 0.15), "read_speed_ms": (1500, 2500)},
    "curious": {"type_delay_ms": (80, 150), "typo_chance": (0.02, 0.08), "read_speed_ms": (2500, 4000)},
    "relaxed": {"type_delay_ms": (100, 200), "typo_chance": (0.01, 0.05), "read_speed_ms": (3000, 5000)},
}

_SEARCH_BEHAVIOR = {
    "hurried": {
        "competitor_clicks": (0, 1),
        "glance_count": (1, 3),
        "snippet_read_s": (2.0, 5.0),
        "hesitation_s": (0.3, 0.8),
        "try_related_first": 0.15,
    },
    "curious": {
        "competitor_clicks": (1, 3),
        "glance_count": (3, 6),
        "snippet_read_s": (4.0, 8.0),
        "hesitation_s": (0.8, 2.0),
        "try_related_first": 0.40,
    },
    "relaxed": {
        "competitor_clicks": (1, 2),
        "glance_count": (2, 5),
        "snippet_read_s": (3.0, 7.0),
        "hesitation_s": (1.0, 2.5),
        "try_related_first": 0.25,
    },
}

# ─── helpers ─────────────────────────────────────────────────────────────────

def _pick_subtokens(url: str) -> list[str]:
    """Rút vài token từ URL để làm hint tạo persona."""
    clean = url.replace("https://", "").replace("http://", "").split("/")[0]
    parts = clean.replace("www.", "").split(".")
    if len(parts) >= 2:
        return [parts[0]]
    return []


# ─── public API ──────────────────────────────────────────────────────────────

async def generate_user_persona(target_url: str) -> PersonaConfig:
    """
    Tạo nhân cách ngẫu nhiên dựa trên URL target.
    Trả về dict: age, mood, gender, type_delay_ms, typo_chance, read_speed_ms.
    """
    mood = random.choice(_MOODS)
    gender = random.choice(_GENDERS)

    age_lo, age_hi = _AGE_RANGES[mood]
    age = random.randint(age_lo, age_hi)

    params = _PERSONA_PARAMS[mood]
    type_delay_ms = random.randint(*params["type_delay_ms"])
    typo_chance = round(random.uniform(*params["typo_chance"]), 3)
    read_speed_ms = random.randint(*params["read_speed_ms"])

    return {
        "age": age,
        "mood": mood,
        "gender": gender,
        "type_delay_ms": type_delay_ms,
        "typo_chance": typo_chance,
        "read_speed_ms": read_speed_ms,
    }


async def generate_search_behavior(keyword: str) -> dict[str, Any]:
    """
    Tạo hành vi tìm kiếm dựa trên keyword.
    Trả về dict: competitor_clicks, glance_count, snippet_read_s, try_related_first.
    """
    # Dùng keyword làm seed nhẹ để cùng keyword ra result ổn định hơn
    seed = sum(ord(c) for c in keyword)
    rng = random.Random(seed % (2**31))

    mood = rng.choice(_MOODS)
    params = _SEARCH_BEHAVIOR[mood]

    return {
        "competitor_clicks": rng.randint(*params["competitor_clicks"]),
        "glance_count": rng.randint(*params["glance_count"]),
        "snippet_read_s": round(rng.uniform(*params["snippet_read_s"]), 1),
        "hesitation_s": round(rng.uniform(*params["hesitation_s"]), 1),
        "try_related_first": rng.random() < params["try_related_first"],
    }


async def generate_related_keyword(keyword: str) -> str:
    """
    Tạo từ khoá biến thể từ keyword gốc (thêm/bớt từ).
    Nếu không có biến thể hay keyword quá ngắn → trả về keyword gốc.
    """
    words = keyword.strip().split()
    if len(words) <= 1:
        return keyword

    # Các biến thể
    variants = [
        f"{words[0]} {words[-1]} gì",          # "sơn nhà gì"
        f"{keyword} 2025",                       # "sơn nhà 2025"
        f"{keyword} giá rẻ",                     # "sơn nhà giá rẻ"
        f"cách {keyword}",                       # "cách sơn nhà"
        f"{keyword} như thế nào",                # "sơn nhà như thế nào"
        f"{keyword} ở đâu tốt",                  # "sơn nhà ở đâu tốt"
        " ".join(words[:2]),                      # chỉ lấy 2 từ đầu
        " ".join(words[-2:]),                     # chỉ lấy 2 từ cuối
    ]

    # Lọc trùng với keyword gốc
    unique = [v for v in variants if v.lower() != keyword.lower()]
    if not unique:
        return keyword

    return random.choice(unique)
