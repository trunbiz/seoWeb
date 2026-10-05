import itertools
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import config.settings as cfg
from ui import TrafficBotUI


class ContinuousLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_continuous_worker_runs_again_without_rest_until_stopped(self):
        stop = threading.Event()
        calls = []

        async def session(*args):
            calls.append(args)
            if len(calls) == 3:
                stop.set()

        app = SimpleNamespace(stop_event=stop, process_single_session=session)
        with patch.object(cfg, "LOOP_CONTINUOUS", True), patch("ui.asyncio.sleep", AsyncMock()) as sleep, patch("builtins.print"):
            await TrafficBotUI.continuous_worker(app, None, None, itertools.cycle([None]), 1, float("inf"))
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(call.args == (0,) for call in sleep.await_args_list))

    async def test_expired_loop_does_not_start_session(self):
        app = SimpleNamespace(stop_event=threading.Event(), process_single_session=AsyncMock())
        with patch.object(cfg, "LOOP_CONTINUOUS", True), patch("ui.asyncio.sleep", AsyncMock()), patch("builtins.print"):
            await TrafficBotUI.continuous_worker(app, None, None, itertools.cycle([None]), 1, 0)
        app.process_single_session.assert_not_called()
