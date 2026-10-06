import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from utils import onsite_interactions as onsite


class GameJourneyTests(unittest.IsolatedAsyncioTestCase):
    def make_page(self, elements):
        page = MagicMock()
        locator = MagicMock()
        locator.count = AsyncMock(return_value=len(elements))
        locator.all = AsyncMock(return_value=elements)
        locator.wait_for = AsyncMock()
        locator.first.wait_for = AsyncMock()
        page.locator.return_value = locator
        return page

    async def test_mandatory_order_and_wait_even_with_short_ui_budget(self):
        element = SimpleNamespace(is_visible=AsyncMock(return_value=True),
                                  is_enabled=AsyncMock(return_value=True))
        landing, game, play = [self.make_page([element]) for _ in range(3)]
        events = []

        async def browse(page, seconds):
            events.append(('browse', page, seconds))

        async def click(page, target):
            events.append(('click', page))
            return game if page is landing else play

        async def sleep(seconds):
            events.append(('wait', seconds))

        with patch.object(onsite, '_browse_game_page', side_effect=browse), \
                patch.object(onsite, '_click_game_element', side_effect=click), \
                patch.object(onsite, 'auto_close_popups', AsyncMock()), \
                patch.object(onsite.random, 'randint', side_effect=[90, 30]), \
                patch.object(onsite.asyncio, 'sleep', side_effect=sleep), \
                patch.object(onsite, '_rich_on_site_interaction', AsyncMock()) as extra:
            # The mandatory flow is outside the one-second optional budget.
            await onsite.rich_on_site_interaction(landing, 'game', duration=0)
        self.assertEqual(events, [('browse', landing, 90), ('click', landing),
                                  ('browse', game, 30), ('click', game), ('wait', 180),
                                  ('click', play)])
        play.locator.assert_called_once_with('#game-frame')
        extra.assert_not_awaited()

    async def test_optional_actions_resume_on_destination_after_wait(self):
        landing, destination = MagicMock(), MagicMock()
        with patch.object(onsite, 'game_card_journey', AsyncMock(return_value=(destination, True))), \
                patch.object(onsite, '_rich_on_site_interaction', AsyncMock()) as extra:
            await onsite.rich_on_site_interaction(landing, 'game')
        extra.assert_awaited_once_with(destination, 'game', 3, None)

    async def test_page_without_cards_keeps_existing_flow(self):
        page = self.make_page([])
        with patch.object(onsite, '_browse_game_page', AsyncMock()) as browse:
            self.assertEqual(await onsite.game_card_journey(page), (page, False))
        browse.assert_not_awaited()

    async def test_missing_accent_button_continues_normal_actions(self):
        card = SimpleNamespace(is_visible=AsyncMock(return_value=True))
        landing, game = self.make_page([card]), self.make_page([])
        with patch.object(onsite, '_browse_game_page', AsyncMock()), \
                patch.object(onsite, '_click_game_element', AsyncMock(return_value=game)), \
                patch.object(onsite, 'auto_close_popups', AsyncMock()), \
                patch.object(onsite, '_rich_on_site_interaction', AsyncMock()) as extra:
            await onsite.rich_on_site_interaction(landing, 'game', duration=1)
        extra.assert_awaited_once_with(game, 'game', 3, 1)

    async def test_hidden_cards_continue_normal_actions(self):
        card = SimpleNamespace(is_visible=AsyncMock(return_value=False))
        page = self.make_page([card])
        with patch.object(onsite, '_browse_game_page', AsyncMock()), \
                patch.object(onsite, '_click_game_element', AsyncMock()) as click, \
                patch.object(onsite, '_rich_on_site_interaction', AsyncMock()) as extra:
            await onsite.rich_on_site_interaction(page, 'game')
        click.assert_not_awaited()
        extra.assert_awaited_once_with(page, 'game', 3, None)

    async def test_missing_button_or_frame_timeout_continues_normal_actions(self):
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        for missing in ('button', 'frame'):
            with self.subTest(missing=missing):
                element = SimpleNamespace(is_visible=AsyncMock(return_value=True),
                                          is_enabled=AsyncMock(return_value=True))
                landing, game, play = [self.make_page([element]) for _ in range(3)]
                if missing == 'button':
                    game.locator.return_value.first.wait_for.side_effect = PlaywrightTimeoutError('missing')
                else:
                    play.locator.return_value.wait_for.side_effect = PlaywrightTimeoutError('missing')
                with patch.object(onsite, '_browse_game_page', AsyncMock()), \
                        patch.object(onsite, '_click_game_element', AsyncMock(side_effect=[game, play])) as click, \
                        patch.object(onsite, 'auto_close_popups', AsyncMock()), \
                        patch.object(onsite.asyncio, 'sleep', AsyncMock()) as sleep, \
                        patch.object(onsite, '_rich_on_site_interaction', AsyncMock()) as extra:
                    await onsite.rich_on_site_interaction(landing, 'game', duration=1)
                destination = game if missing == 'button' else play
                extra.assert_awaited_once_with(destination, 'game', 3, 1)
                self.assertEqual(click.await_count, 1 if missing == 'button' else 2)
                if missing == 'button':
                    sleep.assert_not_awaited()
                else:
                    sleep.assert_awaited_once_with(180)

    async def test_click_follows_popup_and_removes_listener(self):
        from playwright._impl._impl_to_api_mapping import ImplToApiMapping

        page, popup = MagicMock(), MagicMock()
        # Use Playwright's real callback wrapper: MagicMock alone accepts builtins
        # that Page.on rejects because they cannot hold its internal attributes.
        mapping = ImplToApiMapping()
        page.on.side_effect = lambda event, handler: mapping.wrap_handler(handler)
        popup.wait_for_load_state = AsyncMock()
        element = SimpleNamespace(scroll_into_view_if_needed=AsyncMock(),
                                  bounding_box=AsyncMock(return_value=None))

        async def click(**kwargs):
            page.on.call_args.args[1](popup)

        element.click = AsyncMock(side_effect=click)
        with patch.object(onsite.asyncio, 'sleep', AsyncMock()):
            self.assertIs(await onsite._click_game_element(page, element), popup)
        popup.wait_for_load_state.assert_awaited_once()
        page.remove_listener.assert_called_once_with('popup', page.on.call_args.args[1])
