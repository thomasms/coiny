import unittest
from typing import Any

from coiny.core import CoinPrice, CoinyQueue, CoinySession, price_now_url, price_task
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


class PriceTaskTests(unittest.IsolatedAsyncioTestCase):
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

    async def test_price_task_real_eth(self):
        queue = CoinyQueue()
        await queue.put(("ethereum", "eur", price_now_url("ethereum", "eur")))

        async with CoinySession() as session:
            result = await price_task(queue, session)
            # no way to test the live price of course
            half_expected = CoinPrice(fiat="eur", coin="ethereum", rate=0.0)
            self.assertEqual(half_expected.fiat, result.fiat)
            self.assertEqual(half_expected.coin, result.coin)


__all__ = ["PriceTaskTests"]
