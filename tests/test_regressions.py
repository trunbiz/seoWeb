import asyncio
import os
import tempfile
import threading
import unittest
from unittest.mock import patch

import config.settings as cfg
from tests.test_search_flow import _is_captcha
from utils import ai_engine
from utils import rate_limiter


class _FakeLocator:
    def __init__(self, visible=False):
        self._visible = visible

    @property
    def first(self):
        return self

    async def is_visible(self, timeout=500):
        return self._visible


class _FakePage:
    def __init__(self, url, captcha_visible=False):
        self.url = url
        self._captcha_visible = captcha_visible

    def locator(self, selector):
        return _FakeLocator(self._captcha_visible)


class CaptchaRegressionTests(unittest.TestCase):
    def test_normal_google_page_is_not_captcha(self):
        page = _FakePage("https://www.google.com/search?q=test")
        self.assertFalse(asyncio.run(_is_captcha(page)))

    def test_captcha_url_is_detected(self):
        page = _FakePage("https://www.google.com/sorry/index")
        self.assertTrue(asyncio.run(_is_captcha(page)))

    def test_visible_captcha_element_is_detected(self):
        page = _FakePage("https://www.google.com/search?q=test", captcha_visible=True)
        self.assertTrue(asyncio.run(_is_captcha(page)))


class RateLimiterRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_state_file = rate_limiter.STATE_FILE
        rate_limiter.STATE_FILE = os.path.join(self.temp_dir.name, "session_state.json")

    def tearDown(self):
        rate_limiter.STATE_FILE = self.original_state_file
        self.temp_dir.cleanup()

    def test_acquire_reserves_slot_immediately(self):
        first, _ = rate_limiter.acquire_session(max_per_day=25, min_interval=300)
        second, reason = rate_limiter.acquire_session(max_per_day=25, min_interval=300)

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertIn("Cooldown", reason)

    def test_unlimited_mode_ignores_daily_cap_and_interval_but_counts_sessions(self):
        for _ in range(5):
            allowed, _ = rate_limiter.acquire_session(max_per_day=0, min_interval=0)
            self.assertTrue(allowed)
        self.assertEqual(rate_limiter.get_today_summary(max_per_day=3)["ran"], 5)
        allowed, _ = rate_limiter.acquire_session(max_per_day=3, min_interval=0)
        self.assertFalse(allowed)

    def test_concurrent_acquire_does_not_exceed_daily_limit(self):
        results = []

        def acquire():
            allowed, _ = rate_limiter.acquire_session(max_per_day=3, min_interval=0)
            results.append(allowed)

        workers = [threading.Thread(target=acquire) for _ in range(12)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        self.assertEqual(sum(results), 3)
        self.assertEqual(rate_limiter.get_today_summary(max_per_day=3)["ran"], 3)

    def test_different_workers_can_start_during_same_cooldown(self):
        first, _ = rate_limiter.acquire_session(
            max_per_day=25, min_interval=300, scope="worker-1"
        )
        second, _ = rate_limiter.acquire_session(
            max_per_day=25, min_interval=300, scope="worker-2"
        )
        repeated, reason = rate_limiter.acquire_session(
            max_per_day=25, min_interval=300, scope="worker-1"
        )

        self.assertTrue(first)
        self.assertTrue(second)
        self.assertFalse(repeated)
        self.assertIn("Cooldown", reason)


class _FakeGeminiResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        import json
        return {
            "candidates": [{
                "content": {"parts": [{"text": json.dumps(self._payload)}]}
            }]
        }


class GeminiRegressionTests(unittest.TestCase):
    def setUp(self):
        self.old_provider = cfg.AI_PROVIDER
        self.old_key = cfg.GEMINI_API_KEY
        self.old_model = cfg.GEMINI_MODEL

    def tearDown(self):
        cfg.AI_PROVIDER = self.old_provider
        cfg.GEMINI_API_KEY = self.old_key
        cfg.GEMINI_MODEL = self.old_model

    def test_missing_key_uses_local_fallback(self):
        cfg.AI_PROVIDER = "gemini"
        cfg.GEMINI_API_KEY = ""
        persona = asyncio.run(ai_engine.generate_user_persona("https://example.com"))
        self.assertIn(persona["mood"], ("hurried", "curious", "relaxed"))

    @patch("utils.ai_engine.requests.post")
    def test_gemini_persona_uses_structured_response(self, mock_post):
        cfg.AI_PROVIDER = "gemini"
        cfg.GEMINI_API_KEY = "test-key"
        cfg.GEMINI_MODEL = "gemini-3.5-flash"
        mock_post.return_value = _FakeGeminiResponse({
            "age": 29,
            "mood": "curious",
            "gender": "female",
            "type_delay_ms": 90,
            "typo_chance": 0.04,
            "read_speed_ms": 2800,
        })

        persona = asyncio.run(ai_engine.generate_user_persona("https://example.com"))

        self.assertEqual(persona["age"], 29)
        self.assertEqual(persona["mood"], "curious")
        called_url = mock_post.call_args.args[0]
        self.assertIn("gemini-3.5-flash:generateContent", called_url)


if __name__ == "__main__":
    unittest.main()
