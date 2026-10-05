# utils/ai_engine.py
"""AI engine hỗ trợ Gemini, AI Box và bộ sinh local."""

import asyncio
import json
import math
from datetime import date
import random
from typing import Any

import requests

import config.settings as cfg

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

_PERSONA_SCHEMA = {
    "type": "object",
    "properties": {
        "age": {"type": "integer", "minimum": 18, "maximum": 65},
        "mood": {"type": "string", "enum": _MOODS},
        "gender": {"type": "string", "enum": _GENDERS},
        "type_delay_ms": {"type": "integer", "minimum": 30, "maximum": 250},
        "typo_chance": {"type": "number", "minimum": 0, "maximum": 0.2},
        "read_speed_ms": {"type": "integer", "minimum": 1000, "maximum": 6000},
    },
    "required": ["age", "mood", "gender", "type_delay_ms", "typo_chance", "read_speed_ms"],
}

_BEHAVIOR_SCHEMA = {
    "type": "object",
    "properties": {
        "competitor_clicks": {"type": "integer", "minimum": 0, "maximum": 3},
        "glance_count": {"type": "integer", "minimum": 1, "maximum": 6},
        "snippet_read_s": {"type": "number", "minimum": 1, "maximum": 10},
        "hesitation_s": {"type": "number", "minimum": 0.1, "maximum": 3},
        "try_related_first": {"type": "boolean"},
    },
    "required": ["competitor_clicks", "glance_count", "snippet_read_s", "hesitation_s", "try_related_first"],
}

_KEYWORD_SCHEMA = {
    "type": "object",
    "properties": {"keyword": {"type": "string"}},
    "required": ["keyword"],
}

_gemini_warning_shown = False

# ─── helpers ─────────────────────────────────────────────────────────────────

def _pick_subtokens(url: str) -> list[str]:
    """Rút vài token từ URL để làm hint tạo persona."""
    clean = url.replace("https://", "").replace("http://", "").split("/")[0]
    parts = clean.replace("www.", "").split(".")
    if len(parts) >= 2:
        return [parts[0]]
    return []


def _use_remote() -> bool:
    provider = cfg.AI_PROVIDER.strip().lower()
    if provider == "local":
        return False
    if provider not in ("gemini", "aibox", "maxmorus"):
        raise ValueError(f"Unsupported AI_PROVIDER: {provider}")
    key_name = f"{provider.upper()}_API_KEY"
    if getattr(cfg, key_name).strip():
        return True
    if not cfg.AI_FALLBACK_LOCAL:
        raise RuntimeError(f"Missing {key_name}")
    _warn_and_fallback(f"Missing {key_name}")
    return False


def _validate_result(result, schema):
    if not isinstance(result, dict):
        raise ValueError("AI response must be a JSON object")
    for name in schema.get("required", []):
        if name not in result:
            raise ValueError(f"AI response missing field: {name}")
    for name, rule in schema.get("properties", {}).items():
        if name not in result:
            continue
        value = result[name]
        kind = rule["type"]
        valid = {
            "string": isinstance(value, str),
            "boolean": type(value) is bool,
            "integer": type(value) is int,
            "number": type(value) in (int, float),
        }.get(kind, False)
        if not valid:
            raise ValueError(f"Invalid AI field type: {name}")
        if kind in ("integer", "number"):
            if not math.isfinite(value):
                raise ValueError(f"Non-finite AI field: {name}")
        if kind == "string" and not value.strip():
            raise ValueError(f"Empty AI field: {name}")
    return result


async def _provider_json(prompt, schema):
    if cfg.AI_PROVIDER.strip().lower() == "aibox":
        result = await _aibox_json(prompt, schema)
    elif cfg.AI_PROVIDER.strip().lower() == "maxmorus":
        result = await _maxmorus_json(prompt, schema)
    else:
        result = await _gemini_json(prompt, schema)
    return _validate_result(result, schema)


async def _aibox_json(prompt, schema):
    return await _chat_json(prompt, schema, "AIBOX", "AI Box")


async def _maxmorus_json(prompt, schema):
    return await _chat_json(prompt, schema, "MAXMORUS", "MaxMorus", stream=False)


async def _chat_json(prompt, schema, prefix, label, **options):
    key_name = f"{prefix}_API_KEY"
    api_key = getattr(cfg, key_name)
    api_url = getattr(cfg, f"{prefix}_API_URL")
    model = getattr(cfg, f"{prefix}_MODEL")
    if not api_key.strip():
        raise RuntimeError(f"Missing {key_name}")
    response = await asyncio.to_thread(
        requests.post,
        api_url.strip(),
        headers={"Authorization": f"Bearer {api_key.strip()}",
                 "Content-Type": "application/json"},
        json={"model": model.strip(), "messages": [
            {"role": "system", "content": "Return only a JSON object matching this schema: " + json.dumps(schema)},
            {"role": "user", "content": prompt},
        ], **options},
        timeout=30,
    )
    response.raise_for_status()
    try:
        choice = response.json()["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise ValueError(f"{label} response is incomplete")
        content = choice["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"{label} response has no message content") from exc
    if not isinstance(content, str) or not content.strip():
        raise ValueError(f"{label} returned empty content")
    content = content.strip()
    if content.startswith("```") and content.endswith("```"):
        content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return _validate_result(json.loads(content), schema)


async def test_aibox_connection() -> tuple[bool, str]:
    try:
        result = await _aibox_json(
            "Return connection status OK.",
            {"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]},
        )
        return True, result["status"]
    except Exception as exc:
        return False, str(exc)


async def test_maxmorus_connection() -> tuple[bool, str]:
    try:
        result = await _maxmorus_json(
            "Return connection status OK.",
            {"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]},
        )
        return True, result["status"]
    except Exception as exc:
        return False, str(exc)


def _warn_and_fallback(error: Exception | str):
    global _gemini_warning_shown
    if not _gemini_warning_shown:
        message = f"   [AI] {cfg.AI_PROVIDER} unavailable, using local fallback: {str(error)[:120]}"
        try:
            print(message)
        except UnicodeEncodeError:
            print(message.encode("ascii", errors="replace").decode("ascii"))
        _gemini_warning_shown = True


async def _gemini_json(prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Gọi Gemini Generate Content API và trả structured JSON."""
    if not cfg.GEMINI_API_KEY.strip():
        raise RuntimeError("Chưa cấu hình GEMINI_API_KEY")

    endpoint = (
        f"{cfg.GEMINI_API_URL.rstrip('/')}/models/"
        f"{cfg.GEMINI_MODEL}:generateContent"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
            "maxOutputTokens": 512,
        },
    }
    response = await asyncio.to_thread(
        requests.post,
        endpoint,
        headers={
            "x-goog-api-key": cfg.GEMINI_API_KEY.strip(),
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    try:
        text = body["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Gemini trả về response không có nội dung") from exc
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("Gemini không trả về JSON object")
    return result


async def test_gemini_connection() -> tuple[bool, str]:
    """Kiểm tra API key và model bằng một structured-output request nhỏ."""
    try:
        result = await _gemini_json(
            "Return a short connection status.",
            {"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]},
        )
        return True, str(result.get("status", "OK"))
    except Exception as exc:
        return False, str(exc)


def _local_user_persona() -> PersonaConfig:
    mood = random.choice(_MOODS)
    gender = random.choice(_GENDERS)
    age_lo, age_hi = _AGE_RANGES[mood]
    params = _PERSONA_PARAMS[mood]
    return {
        "age": random.randint(age_lo, age_hi),
        "mood": mood,
        "gender": gender,
        "type_delay_ms": random.randint(*params["type_delay_ms"]),
        "typo_chance": round(random.uniform(*params["typo_chance"]), 3),
        "read_speed_ms": random.randint(*params["read_speed_ms"]),
    }


def _local_search_behavior(keyword: str) -> dict[str, Any]:
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


# ─── public API ──────────────────────────────────────────────────────────────

async def generate_user_persona(target_url: str) -> PersonaConfig:
    """
    Tạo nhân cách ngẫu nhiên dựa trên URL target.
    Trả về dict: age, mood, gender, type_delay_ms, typo_chance, read_speed_ms.
    """
    if _use_remote():
        try:
            result = await _provider_json(
                f"Create one realistic Vietnamese website visitor persona for {target_url}. Vary the persona naturally.",
                _PERSONA_SCHEMA,
            )
            return {
                "age": max(18, min(65, int(result["age"]))),
                "mood": result["mood"] if result["mood"] in _MOODS else "curious",
                "gender": result["gender"] if result["gender"] in _GENDERS else "female",
                "type_delay_ms": max(30, min(250, int(result["type_delay_ms"]))),
                "typo_chance": max(0.0, min(0.2, float(result["typo_chance"]))),
                "read_speed_ms": max(1000, min(6000, int(result["read_speed_ms"]))),
            }
        except Exception as exc:
            if not cfg.AI_FALLBACK_LOCAL:
                raise
            _warn_and_fallback(exc)
    return _local_user_persona()


async def generate_search_behavior(keyword: str) -> dict[str, Any]:
    """
    Tạo hành vi tìm kiếm dựa trên keyword.
    Trả về dict: competitor_clicks, glance_count, snippet_read_s, try_related_first.
    """
    if _use_remote():
        try:
            result = await _provider_json(
                f"Create realistic Google search behavior for a Vietnamese user searching for: {keyword}",
                _BEHAVIOR_SCHEMA,
            )
            return {
                "competitor_clicks": max(0, min(3, int(result["competitor_clicks"]))),
                "glance_count": max(1, min(6, int(result["glance_count"]))),
                "snippet_read_s": max(1.0, min(10.0, float(result["snippet_read_s"]))),
                "hesitation_s": max(0.1, min(3.0, float(result["hesitation_s"]))),
                "try_related_first": bool(result["try_related_first"]),
            }
        except Exception as exc:
            if not cfg.AI_FALLBACK_LOCAL:
                raise
            _warn_and_fallback(exc)
    return _local_search_behavior(keyword)


async def generate_related_keyword(keyword: str) -> str:
    """
    Tạo từ khoá biến thể từ keyword gốc (thêm/bớt từ).
    Nếu không có biến thể hay keyword quá ngắn → trả về keyword gốc.
    """
    if _use_remote():
        try:
            result = await _provider_json(
                f"Create one natural Vietnamese search query variation for: {keyword}",
                _KEYWORD_SCHEMA,
            )
            related = str(result["keyword"]).strip()
            if related and related.lower() != keyword.lower():
                return related[:200]
        except Exception as exc:
            if not cfg.AI_FALLBACK_LOCAL:
                raise
            _warn_and_fallback(exc)

    words = keyword.strip().split()
    if len(words) <= 1:
        return keyword

    # Các biến thể
    variants = [
        f"{words[0]} {words[-1]} gì",          # "sơn nhà gì"
        f"{keyword} {date.today().year}",                       # "sơn nhà 2025"
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
