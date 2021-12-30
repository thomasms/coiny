import unittest
from typing import Any

from coiny.core import CoinPrice, CoinyQueue, CoinySession, price_task
from coiny.utils import NullCoinPrice


class HasJson:
    def __init__(self, data) -> None:
        self.data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        pass

    async def json(self):
        return self.data


class CoreUnitTests(unittest.IsolatedAsyncioTestCase):
    async def test_price_task_empty_queue(self):
        queue = CoinyQueue()
        session = CoinySession()
        result = await price_task(queue, session)
        self.assertEqual(NullCoinPrice, result)

    async def test_price_task_queue(self):
        class NoGetSession(CoinySession):
            """HACK: Not a good idea to inherit from CoinySession"""

            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                self.mock_url = ""

            def get(
                self, url: str, *, allow_redirects: bool = True, **kwargs: Any
            ) -> HasJson:
                self.mock_url = f"called:{url}"
                return HasJson({"mycoin": {"XYZ": 3.4}})

        queue = CoinyQueue()
        await queue.put(("mycoin", "XYZ", "https://myurl"))

        async with NoGetSession() as session:
            result = await price_task(queue, session)

            expected = CoinPrice(fiat="XYZ", coin="mycoin", rate=3.4)
            self.assertEqual(expected, result)
            self.assertEqual("called:https://myurl", session.mock_url)

    async def test_price_task_mock_eth(self):
        mock_url = "https://run.mocky.io/v3/09750cfe-39a5-4d31-9651-2292765a8fe3"
        # returns -> {"ethereum": {"eur": 3295.23}}

        queue = CoinyQueue()
        await queue.put(("ethereum", "eur", mock_url))

        async with CoinySession() as session:
            result = await price_task(queue, session)
            expected = CoinPrice(fiat="eur", coin="ethereum", rate=3295.23)
            self.assertEqual(expected, result)

    async def test_price_task_mock_eth_invalid(self):
        mock_url = "https://run.mocky.io/v3/09750cfe-39a5-4d31-9651-2292765a8fe3"

        queue = CoinyQueue()
        await queue.put(("bitcoin", "gbp", mock_url))

        async with CoinySession() as session:
            result = await price_task(queue, session)
            self.assertEqual(NullCoinPrice, result)


__all__ = ["CoreUnitTests"]
