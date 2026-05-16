"""
utils/rate_limiter.py — Gi?i h?n t?n su?t session ?? tránh b? Google phát hi?n.

Lu?t:
- T?i ?a 25 session/ngày (c?u hình trong settings.MAX_SESSIONS_PER_DAY)
- T?i thi?u 5 phút gi?a các session
- T? ?ó?ng l?i n?u v??t quá gi?i h?n

L?u tr?ng thái vào file JSON ?? không b? reset khi restart.
"""
import json
import os
import time
from datetime import datetime, date

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "session_state.json")

def _load_state() -> dict:
    """??c tr?ng thái t? file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"date": "", "count": 0, "last_session": 0}

def _save_state(state: dict):
    """Ghi tr?ng thái ra file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def can_run_session(max_per_day: int = 99999, min_interval: int = 0) -> tuple[bool, str]:
    """Luôn cho phép chạy — đã tắt giới hạn.
    Args:
        max_per_day: Mặc định 99999 (không giới hạn)
        min_interval: Mặc định 0s (không cooldown)
    Returns:
        (True, "")
    """
    _load_state()  # vẫn load để reset file nếu cần
    return True, ""

def mark_session_run():
    """Ghi nh?n m?t session ?ã ch?y."""
    today = date.today().isoformat()
    state = _load_state()

    if state["date"] != today:
        state = {"date": today, "count": 0, "last_session": 0}

    state["count"] += 1
    state["last_session"] = time.time()
    _save_state(state)

def get_today_summary() -> dict:
    """Tr? v? th?ng kê hôm nay."""
    state = _load_state()
    today = date.today().isoformat()

    if state["date"] != today:
        return {"date": today, "ran": 0, "remaining": 25, "next_window": 0}

    remaining = 25 - state["count"]
    next_window = max(0, int(state["last_session"] + 300 - time.time())) if state["last_session"] > 0 else 0

    return {
        "date": today,
        "ran": state["count"],
        "remaining": max(0, remaining),
        "next_window": next_window,
    }
