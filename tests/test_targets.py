import asyncio
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from contextlib import ExitStack
import ui
import config.settings as cfg
from utils.targets import current_target, get_target_url, parse_targets
from utils.onsite_interactions import rich_on_site_interaction

class TargetTests(unittest.IsolatedAsyncioTestCase):
    def test_validation_and_deduplication(self):
        self.assertEqual(parse_targets("https://a.example\n\nhttps://b.example\nhttps://a.example"), ["https://a.example", "https://b.example"])
        for invalid in ("", "example.com", "https://a.example:bad", "https://a .example"):
            with self.assertRaises(ValueError):
                parse_targets(invalid)

    async def test_targets_are_isolated_between_tasks(self):
        async def visit(url):
            token = current_target.set(url)
            try:
                await asyncio.sleep(0)
                return get_target_url()
            finally:
                current_target.reset(token)
        self.assertEqual(await asyncio.gather(visit("https://a.example"), visit("https://b.example")), ["https://a.example", "https://b.example"])
        self.assertEqual(get_target_url(), cfg.TARGET_URL)

    async def test_modes_visit_remaining_targets_after_exception(self):
        for mode, flow_path in (
            ("direct", "ui.run_deep_session"),
            ("search", "tests.test_search_flow.run_search_flow"),
            ("aio", "scenarios.aio_traffic.run_aio_session"),
            ("mix", "tests.test_search_flow.run_search_flow"),
        ):
            with self.subTest(mode=mode), ExitStack() as stack:
                visited = []
                async def visit(page, *args, **kwargs):
                    visited.append(get_target_url())
                    if len(visited) == 1:
                        raise RuntimeError("first website failed")
                    return True
                page = SimpleNamespace(context=SimpleNamespace(close=AsyncMock()))
                manager = SimpleNamespace(create_context=AsyncMock(return_value=page))
                app = SimpleNamespace(stop_event=threading.Event(), after=lambda *args: None, _inc_ok=lambda: None, _inc_err=lambda: None)
                for name, value in (("TARGET_URLS", ["https://a.example", "https://b.example"]), ("WARMUP_ENABLE", False), ("TRAFFIC_MODE", mode)):
                    stack.enter_context(patch.object(cfg, name, value))
                stack.enter_context(patch("utils.rate_limiter.acquire_session", return_value=(True, "")))
                stack.enter_context(patch(flow_path, side_effect=visit))
                stack.enter_context(patch("ui.random.random", return_value=0.1))
                stack.enter_context(patch("builtins.print"))
                await ui.ZizaSeoUI.process_single_session(app, manager, None, None, 1)
                self.assertEqual(visited, ["https://a.example", "https://b.example"])
                self.assertEqual(get_target_url(), cfg.TARGET_URL)
                page.context.close.assert_awaited_once()

    async def test_stop_prevents_visiting_next_target(self):
        visited = []
        app = SimpleNamespace(stop_event=threading.Event(), after=lambda *args: None, _inc_ok=lambda: None, _inc_err=lambda: None)
        async def visit(page, duration):
            visited.append(get_target_url())
            app.stop_event.set()
            return True
        page = SimpleNamespace(context=SimpleNamespace(close=AsyncMock()))
        manager = SimpleNamespace(create_context=AsyncMock(return_value=page))
        with patch.object(cfg, "TARGET_URLS", ["https://a.example", "https://b.example"]), patch.object(cfg, "WARMUP_ENABLE", False), patch.object(cfg, "TRAFFIC_MODE", "direct"), patch("utils.rate_limiter.acquire_session", return_value=(True, "")), patch.object(ui, "run_deep_session", side_effect=visit), patch("builtins.print"):
            await ui.ZizaSeoUI.process_single_session(app, manager, None, None, 1)
        self.assertEqual(visited, ["https://a.example"])
        self.assertEqual(get_target_url(), cfg.TARGET_URL)
        page.context.close.assert_awaited_once()

    async def test_session_visits_all_targets_in_same_context(self):
        visited = []
        async def visit(page, duration):
            visited.append((get_target_url(), duration))
            return len(visited) != 1
        page = SimpleNamespace(context=SimpleNamespace(close=AsyncMock()))
        manager = SimpleNamespace(create_context=AsyncMock(return_value=page))
        app = SimpleNamespace(stop_event=threading.Event(), after=lambda *args: None, _inc_ok=lambda: None, _inc_err=lambda: None)
        with patch.object(cfg, "TARGET_URLS", ["https://a.example", "https://b.example"], create=True), patch.object(cfg, "WARMUP_ENABLE", False), patch.object(cfg, "TRAFFIC_MODE", "direct"), patch.object(cfg, "DURATION_MIN", 12), patch.object(cfg, "DURATION_MAX", 12), patch("utils.rate_limiter.acquire_session", return_value=(True, "")), patch.object(ui, "run_deep_session", side_effect=visit), patch("builtins.print"):
            await ui.ZizaSeoUI.process_single_session(app, manager, None, None, 1)
        self.assertEqual(visited, [("https://a.example", 12), ("https://b.example", 12)])
        manager.create_context.assert_awaited_once()
        page.context.close.assert_awaited_once()
        self.assertEqual(get_target_url(), cfg.TARGET_URL)

    async def test_onsite_actions_cannot_exceed_budget(self):
        cancelled = asyncio.Event()
        async def slow(*args):
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.set()
        with patch("utils.onsite_interactions._rich_on_site_interaction", side_effect=slow):
            await rich_on_site_interaction(None, "", duration=0.01)
        self.assertTrue(cancelled.is_set())
