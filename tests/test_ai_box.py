import asyncio
import json
import unittest
from unittest.mock import patch, Mock

import requests
import config.settings as cfg
from utils import ai_engine as ai


class AIBoxTests(unittest.TestCase):
    def setUp(self):
        self.config = patch.multiple(cfg, AI_PROVIDER="aibox", AIBOX_API_KEY="test-key",
                                     AI_FALLBACK_LOCAL=False)
        self.config.start()
        self.addCleanup(self.config.stop)
        self.post = patch("utils.ai_engine.requests.post").start()
        self.addCleanup(patch.stopall)

    def response(self, content, reason="stop"):
        self.post.return_value = Mock()
        self.post.return_value.json.return_value = {
            "choices": [{"finish_reason": reason, "message": {
                "content": content, "reasoning_content": "not the answer"}}]}

    def keyword(self):
        return asyncio.run(ai.generate_related_keyword("original keyword"))

    def test_request_and_content(self):
        self.response(json.dumps({"keyword": "new keyword"}))
        self.assertEqual(self.keyword(), "new keyword")
        args, kwargs = self.post.call_args
        self.assertEqual(args[0], cfg.AIBOX_API_URL)
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["model"], cfg.AIBOX_MODEL)
        self.assertEqual(kwargs["json"]["messages"][1]["role"], "user")
        self.assertEqual(kwargs["timeout"], 30)

    def test_fenced_json(self):
        self.response('```json\n{"keyword":"new keyword"}\n```')
        self.assertEqual(self.keyword(), "new keyword")

    def test_invalid_responses_raise(self):
        for content in (None, "", "not json", "[]", "{}", '{"keyword":null}'):
            with self.subTest(content=content):
                self.response(content)
                with self.assertRaises(ValueError):
                    self.keyword()

    def test_truncated_response_rejected(self):
        self.response('{"keyword":"new keyword"}', "length")
        with self.assertRaises(ValueError):
            self.keyword()

    def test_string_boolean_rejected(self):
        self.response(json.dumps({"competitor_clicks": 1, "glance_count": 2,
                                  "snippet_read_s": 3, "hesitation_s": 1,
                                  "try_related_first": "false"}))
        with self.assertRaises(ValueError):
            asyncio.run(ai.generate_search_behavior("test"))

    def test_network_and_http_errors(self):
        for error in (requests.Timeout(), requests.HTTPError("401")):
            self.post.side_effect = error
            with self.assertRaises(type(error)):
                self.keyword()
            with patch.object(cfg, "AI_FALLBACK_LOCAL", True):
                self.assertIsInstance(self.keyword(), str)

    def test_missing_key(self):
        with patch.object(cfg, "AIBOX_API_KEY", ""):
            with self.assertRaises(RuntimeError):
                self.keyword()
            with patch.object(cfg, "AI_FALLBACK_LOCAL", True):
                self.assertIsInstance(self.keyword(), str)
        self.post.assert_not_called()

    def test_local_never_calls_api(self):
        with patch.object(cfg, "AI_PROVIDER", "local"):
            self.keyword()
        self.post.assert_not_called()

    def test_unknown_provider_rejected(self):
        with patch.object(cfg, "AI_PROVIDER", "typo"):
            with self.assertRaises(ValueError):
                self.keyword()

    def test_connection_does_not_hide_failure_with_fallback(self):
        self.post.side_effect = requests.Timeout("timeout")
        with patch.object(cfg, "AI_FALLBACK_LOCAL", True):
            ok, detail = asyncio.run(ai.test_aibox_connection())
        self.assertFalse(ok)
        self.assertIn("timeout", detail)
