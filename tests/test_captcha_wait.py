import asyncio
import threading
import unittest
from contextlib import ExitStack
from playwright.async_api import TimeoutError as NavigationTimeout
from unittest.mock import AsyncMock, Mock, patch

import config.settings as cfg
from utils import captcha


class CaptchaWaitTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.page = Mock()
        self.page.is_closed.return_value = False
        self.page.bring_to_front = AsyncMock()
        config = patch.multiple(cfg, CAPTCHA_ACTION="manual", HEADLESS_MODE=False, CAPTCHA_WAIT_SECONDS=10,
                                CAPTCHA_COOLDOWN_SECONDS=0)
        config.start()
        self.addCleanup(config.stop)

    async def test_normal_page_continues_without_prompt(self):
        with patch.object(captcha, "is_captcha", AsyncMock(return_value=False)):
            self.assertTrue(await captcha.wait_for_verification(self.page))
        self.page.bring_to_front.assert_not_called()

    async def test_manual_verification_resumes_same_page(self):
        with patch.object(captcha, "is_captcha", AsyncMock(side_effect=[True, False])):
            self.assertTrue(await captcha.wait_for_verification(self.page))
        self.page.bring_to_front.assert_awaited_once()
        self.page.goto.assert_not_called()

    async def test_headless_does_not_wait_for_manual_input(self):
        with patch.object(cfg, "HEADLESS_MODE", True), patch.object(captcha, "is_captcha", AsyncMock(return_value=True)):
            self.assertFalse(await captcha.wait_for_verification(self.page))
        self.page.bring_to_front.assert_not_called()

    async def test_timeout_returns_failure(self):
        with patch.object(cfg, "CAPTCHA_WAIT_SECONDS", 0.01), patch.object(captcha, "is_captcha", AsyncMock(return_value=True)):
            self.assertFalse(await captcha.wait_for_verification(self.page))

    async def test_stop_during_manual_wait(self):
        stop = threading.Event()
        self.page.bring_to_front.side_effect = stop.set
        with patch.object(captcha, "is_captcha", AsyncMock(return_value=True)):
            self.assertFalse(await captcha.wait_for_verification(self.page, stop))

    async def test_stop_interrupts_cooldown(self):
        stop = threading.Event()
        async def stop_on_sleep(_):
            stop.set()
        with patch.multiple(cfg, CAPTCHA_WAIT_SECONDS=0, CAPTCHA_COOLDOWN_SECONDS=60), patch.object(captcha, "is_captcha", AsyncMock(return_value=True)), patch.object(captcha.asyncio, "sleep", side_effect=stop_on_sleep) as sleep:
            self.assertFalse(await captcha.wait_for_verification(self.page, stop))
        sleep.assert_awaited_once()

    async def test_closed_page_returns_failure(self):
        self.page.is_closed.return_value = True
        self.assertFalse(await captcha.wait_for_verification(self.page))

    async def test_direct_mode_never_waits_for_user(self):
        with patch.object(cfg, "CAPTCHA_ACTION", "direct"), patch.object(captcha, "is_captcha", AsyncMock(return_value=True)), patch.object(captcha.asyncio, "sleep", AsyncMock()) as sleep:
            with self.assertRaises(captcha.GoogleCaptchaDetected):
                await captcha.wait_for_verification(self.page)
        sleep.assert_not_called()
        self.page.bring_to_front.assert_not_called()

    async def test_direct_fallback_uses_target_without_fake_referrer(self):
        self.page.url = cfg.TARGET_URL
        self.page.goto = AsyncMock(return_value=Mock(status=200))
        with patch.object(captcha, "is_captcha", AsyncMock(return_value=False)), patch("utils.onsite_interactions.auto_close_popups", AsyncMock()), patch("utils.onsite_interactions.rich_on_site_interaction", AsyncMock()) as interact:
            self.assertTrue(await captcha.direct_after_captcha(self.page, 45))
        self.page.goto.assert_awaited_once_with(cfg.TARGET_URL, referer="", wait_until="domcontentloaded", timeout=60000)
        self.assertEqual(interact.call_args.kwargs["duration"], 45)

    async def test_direct_failure_is_not_reported_as_success(self):
        self.page.goto = AsyncMock(side_effect=RuntimeError("navigation failed"))
        self.assertFalse(await captcha.direct_after_captcha(self.page))

    async def test_direct_does_not_navigate_after_stop(self):
        stop = threading.Event()
        stop.set()
        self.assertFalse(await captcha.direct_after_captcha(self.page, stop_event=stop))
        self.page.goto.assert_not_called()

    async def test_target_captcha_does_not_retry(self):
        self.page.url = cfg.TARGET_URL
        self.page.goto = AsyncMock(return_value=Mock(status=200))
        with patch.object(captcha, "is_captcha", AsyncMock(return_value=True)), patch("utils.onsite_interactions.rich_on_site_interaction", AsyncMock()) as interact:
            self.assertFalse(await captcha.direct_after_captcha(self.page))
        self.page.goto.assert_awaited_once()
        interact.assert_not_called()

    async def test_search_routes_captcha_to_direct(self):
        from tests import test_search_flow as search
        from utils.ai_engine import _local_user_persona, _local_search_behavior
        self.page.goto = AsyncMock()
        with patch.object(search, "generate_user_persona", AsyncMock(return_value=_local_user_persona())), patch.object(search, "generate_search_behavior", AsyncMock(return_value=_local_search_behavior("test"))), patch.object(search, "_warmup_before_search", AsyncMock()), patch.object(search, "_accept_google_consent", AsyncMock()), patch.object(search, "wait_for_verification", AsyncMock(side_effect=captcha.GoogleCaptchaDetected)), patch.object(search, "direct_after_captcha", AsyncMock(return_value=True)) as direct, patch("builtins.print"):
            self.assertTrue(await search.run_search_flow(self.page, 45))
        direct.assert_awaited_once_with(self.page, 45, None)

    async def test_google_timeout_still_navigates_to_target(self):
        from tests import test_search_flow as search
        from utils.ai_engine import _local_user_persona, _local_search_behavior
        self.page.url = cfg.TARGET_URL
        self.page.goto = AsyncMock(side_effect=[NavigationTimeout("Timeout 60000ms exceeded"), Mock(status=200)])
        with ExitStack() as stack:
            stack.enter_context(patch.object(search, "generate_user_persona", AsyncMock(return_value=_local_user_persona())))
            stack.enter_context(patch.object(search, "generate_search_behavior", AsyncMock(return_value=_local_search_behavior("test"))))
            stack.enter_context(patch.object(search, "_warmup_before_search", AsyncMock()))
            stack.enter_context(patch.object(captcha, "is_captcha", AsyncMock(return_value=False)))
            stack.enter_context(patch("utils.onsite_interactions.auto_close_popups", AsyncMock()))
            interaction = stack.enter_context(patch("utils.onsite_interactions.rich_on_site_interaction", AsyncMock()))
            stack.enter_context(patch("builtins.print"))
            self.assertTrue(await search.run_search_flow(self.page, 45))
        self.assertEqual(self.page.goto.await_args_list[0].args[0], "https://www.google.com.vn/")
        self.assertEqual(self.page.goto.await_args_list[1].args[0], cfg.TARGET_URL)
        interaction.assert_awaited_once()

    async def test_target_timeout_retries_then_succeeds(self):
        self.page.url = cfg.TARGET_URL
        self.page.goto = AsyncMock(side_effect=[NavigationTimeout("timeout"), Mock(status=200)])
        with patch.object(cfg, "TARGET_NAVIGATION_ATTEMPTS", 3), patch.object(captcha.asyncio, "sleep", AsyncMock()), patch.object(captcha, "is_captcha", AsyncMock(return_value=False)), patch("utils.onsite_interactions.auto_close_popups", AsyncMock()), patch("utils.onsite_interactions.rich_on_site_interaction", AsyncMock()):
            self.assertTrue(await captcha.visit_target_direct(self.page, 45))
        self.assertEqual(self.page.goto.await_count, 2)

    async def test_target_retries_are_bounded(self):
        self.page.goto = AsyncMock(side_effect=NavigationTimeout("timeout"))
        with patch.object(cfg, "TARGET_NAVIGATION_ATTEMPTS", 3), patch.object(captcha.asyncio, "sleep", AsyncMock()):
            self.assertFalse(await captcha.visit_target_direct(self.page))
        self.assertEqual(self.page.goto.await_count, 3)

    async def test_stop_between_target_retries(self):
        stop = threading.Event()
        self.page.goto = AsyncMock(side_effect=NavigationTimeout("timeout"))
        async def stop_on_sleep(_):
            stop.set()
        with patch.object(captcha.asyncio, "sleep", side_effect=stop_on_sleep):
            self.assertFalse(await captcha.visit_target_direct(self.page, stop_event=stop))
        self.page.goto.assert_awaited_once()

    async def test_no_keywords_uses_direct(self):
        from tests import test_search_flow as search
        with patch.object(cfg, "SEO_KEYWORDS", []), patch.object(search, "visit_target_direct", AsyncMock(return_value=True)) as direct:
            self.assertTrue(await search.run_search_flow(self.page, 45))
        direct.assert_awaited_once_with(self.page, 45, None, reason="NO KEYWORDS")

    async def test_aio_google_timeout_uses_direct(self):
        from scenarios import aio_traffic
        self.page.goto = AsyncMock(side_effect=NavigationTimeout("timeout"))
        with patch.object(captcha, "visit_target_direct", AsyncMock(return_value=True)) as direct, patch("builtins.print"):
            self.assertTrue(await aio_traffic.run_aio_session(self.page))
        direct.assert_awaited_once_with(self.page, cfg.TEST_DURATION, None)
