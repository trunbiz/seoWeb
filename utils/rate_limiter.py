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
import threading
import sys
from pathlib import Path
from datetime import date

import config.settings as cfg

if getattr(sys, "frozen", False):
    _data_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "SeoWeb"
    _data_dir.mkdir(parents=True, exist_ok=True)
    STATE_FILE = str(_data_dir / "session_state.json")
else:
    STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "session_state.json")
_STATE_LOCK = threading.Lock()

def _load_state() -> dict:
    """??c tr?ng thái t? file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                state = json.load(f)
            if not isinstance(state, dict):
                raise ValueError("Invalid session state")
            return {
                "date": str(state.get("date", "")),
                "count": max(0, int(state.get("count", 0))),
                "last_session": max(0, float(state.get("last_session", 0))),
                "last_sessions": {
                    str(key): max(0, float(value))
                    for key, value in state.get("last_sessions", {}).items()
                } if isinstance(state.get("last_sessions", {}), dict) else {},
            }
        except:
            pass
    return {"date": "", "count": 0, "last_session": 0, "last_sessions": {}}

def _save_state(state: dict):
    """Ghi tr?ng thái ra file."""
    temp_file = f"{STATE_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(state, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_file, STATE_FILE)

def can_run_session(
    max_per_day: int | None = None,
    min_interval: int | None = None,
    scope: str = "global",
) -> tuple[bool, str]:
    """Kiểm tra có được chạy session mới không.
    Args:
        max_per_day: Số session tối đa/ngày (mặc định 25)
        min_interval: Giây tối thiểu giữa 2 session (mặc định 300)
    Returns:
        (True, "") nếu được phép, (False, "lý do") nếu bị chặn
    """
    max_per_day = cfg.MAX_SESSIONS_PER_DAY if max_per_day is None else max_per_day
    min_interval = cfg.MIN_INTERVAL_BETWEEN_SESSIONS if min_interval is None else min_interval
    state = _load_state()
    today = date.today().isoformat()

    # Nếu chưa có dữ liệu hôm nay → OK
    if state["date"] != today:
        return True, ""

    # Check giới hạn ngày
    if max_per_day > 0 and state["count"] >= max_per_day:
        next_day = "ngày mai"
        return False, f"Đã đạt giới hạn {max_per_day} session/ngày. Chờ {next_day}."

    # Check cooldown giữa các session
    last_session = state.get("last_sessions", {}).get(scope, 0)
    if scope == "global" and not last_session:
        last_session = state["last_session"]
    if last_session > 0:
        elapsed = time.time() - last_session
        if elapsed < min_interval:
            wait = int(min_interval - elapsed)
            return False, f"Cooldown: chờ {wait}s nữa ({min_interval}s giữa các session)."

    return True, ""


def acquire_session(
    max_per_day: int | None = None,
    min_interval: int | None = None,
    scope: str = "global",
) -> tuple[bool, str]:
    """Kiểm tra và giữ một suất chạy trong cùng một thao tác có khóa."""
    max_per_day = cfg.MAX_SESSIONS_PER_DAY if max_per_day is None else max_per_day
    min_interval = cfg.MIN_INTERVAL_BETWEEN_SESSIONS if min_interval is None else min_interval
    with _STATE_LOCK:
        allowed, reason = can_run_session(max_per_day, min_interval, scope)
        if not allowed:
            return False, reason
        mark_session_run(scope)
        return True, ""

def mark_session_run(scope: str = "global"):
    """Ghi nhận một session đã chạy."""
    today = date.today().isoformat()
    state = _load_state()

    if state["date"] != today:
        state = {"date": today, "count": 0, "last_session": 0, "last_sessions": {}}

    state["count"] += 1
    state["last_session"] = time.time()
    state.setdefault("last_sessions", {})[scope] = state["last_session"]
    _save_state(state)

def get_today_summary(max_per_day: int | None = None, min_interval: int | None = None) -> dict:
    """Trả về thống kê hôm nay."""
    max_per_day = cfg.MAX_SESSIONS_PER_DAY if max_per_day is None else max_per_day
    min_interval = cfg.MIN_INTERVAL_BETWEEN_SESSIONS if min_interval is None else min_interval
    state = _load_state()
    today = date.today().isoformat()

    if state["date"] != today:
        return {"date": today, "ran": 0, "remaining": max_per_day, "next_window": 0}

    remaining = max_per_day - state["count"]
    next_window = max(0, int(state["last_session"] + min_interval - time.time())) if state["last_session"] > 0 else 0

    return {
        "date": today,
        "ran": state["count"],
        "remaining": max(0, remaining),
        "next_window": next_window,
    }
