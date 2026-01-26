import asyncio
import unittest
from typing import Any
from unittest.mock import Mock, AsyncMock, patch

from aiohttp import ClientResponseError, ClientError, ClientConnectorError

from coiny.core import (
    CoinPrice,
    CoinyQueue,
    CoinySession,
    price_task,
    balance_task,
)
from coiny.utils import NullCoinPrice, NullAccount, Account


class MockResponse:
    """Mock response for aiohttp"""

    def __init__(self, data, status=200):
        self.data = data
        self.status = status
        self.reason = "OK" if status == 200 else "Error"

    async def __aenter__(self):
        if self.status != 200:
            raise ClientResponseError(
                request_info=Mock(),
                history=(),
                status=self.status,
                message=self.reason,
                headers={}
            )
        return self

    async def __aexit__(self, *args, **kwargs):
        pass

    async def json(self):
        return self.data

    def raise_for_status(self):
        if self.status != 200:
            raise ClientResponseError(
                request_info=Mock(),
                history=(),
                status=self.status,
                message=self.reason,
                headers={}
            )


class ErrorHandlingTests(unittest.IsolatedAsyncioTestCase):
    """Test error handling and logging in API calls"""

    async def test_price_task_http_error(self):
        """Test that price_task handles HTTP errors gracefully"""
        
        class ErrorSession(CoinySession):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def get(self, url: str, **kwargs: Any):
                return MockResponse({}, status=404)

        queue = CoinyQueue()
        await queue.put(("bitcoin", "usd", "https://example.com"))

        async with ErrorSession() as session:
            result = await price_task(queue, session)
            # Should return NullCoinPrice on error
            self.assertEqual(NullCoinPrice, result)

    async def test_price_task_connection_error(self):
        """Test that price_task handles connection errors gracefully"""
        
        class ConnectionErrorSession(CoinySession):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def get(self, url: str, **kwargs: Any):
                # Return a context manager that raises on entry
                class ErrorContext:
                    async def __aenter__(self):
                        raise ClientConnectorError(Mock(), OSError("Connection failed"))
                    
                    async def __aexit__(self, *args):
                        pass
                
                return ErrorContext()

        queue = CoinyQueue()
        await queue.put(("ethereum", "eur", "https://example.com"))

        async with ConnectionErrorSession() as session:
            result = await price_task(queue, session)
            # Should return NullCoinPrice on error
            self.assertEqual(NullCoinPrice, result)

    async def test_price_task_missing_data(self):
        """Test that price_task handles missing data in response"""
        
        class IncompleteDataSession(CoinySession):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def get(self, url: str, **kwargs: Any):
                # Return response with wrong coin data
                return MockResponse({"othercoin": {"usd": 100}})

        queue = CoinyQueue()
        await queue.put(("bitcoin", "usd", "https://example.com"))

        async with IncompleteDataSession() as session:
            result = await price_task(queue, session)
            # Should return NullCoinPrice when data is missing
            self.assertEqual(NullCoinPrice, result)

    async def test_price_task_success(self):
        """Test that price_task works correctly with valid data"""
        
        class SuccessSession(CoinySession):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def get(self, url: str, **kwargs: Any):
                return MockResponse({"bitcoin": {"usd": 50000.0}})

        queue = CoinyQueue()
        await queue.put(("bitcoin", "usd", "https://example.com"))

        async with SuccessSession() as session:
            result = await price_task(queue, session)
            expected = CoinPrice(coin="bitcoin", fiat="usd", rate=50000.0)
            self.assertEqual(expected, result)

    async def test_balance_task_http_error(self):
        """Test that balance_task handles HTTP errors gracefully"""
        
        class ErrorSession(CoinySession):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def get(self, url: str, **kwargs: Any):
                return MockResponse({}, status=500)

        def mock_account(data, address):
            return Account(balance=1.0, type="BTC", address=address)

        def mock_url(address):
            return f"https://example.com/{address}"

        queue = CoinyQueue()
        await queue.put((mock_account, mock_url, "test_address"))

        async with ErrorSession() as session:
            result = await balance_task(queue, session)
            # Should return NullAccount on error
            self.assertEqual(NullAccount, result)

    async def test_balance_task_connection_error(self):
        """Test that balance_task handles connection errors gracefully"""
        
        class ConnectionErrorSession(CoinySession):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def get(self, url: str, **kwargs: Any):
                class ErrorContext:
                    async def __aenter__(self):
                        raise ClientConnectorError(Mock(), OSError("Connection failed"))
                    
                    async def __aexit__(self, *args):
                        pass
                
                return ErrorContext()

        def mock_account(data, address):
            return Account(balance=1.0, type="ETH", address=address)

        def mock_url(address):
            return f"https://example.com/{address}"

        queue = CoinyQueue()
        await queue.put((mock_account, mock_url, "test_address"))

        async with ConnectionErrorSession() as session:
            result = await balance_task(queue, session)
            # Should return NullAccount on error
            self.assertEqual(NullAccount, result)

    async def test_balance_task_success(self):
        """Test that balance_task works correctly with valid data"""
        
        class SuccessSession(CoinySession):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def get(self, url: str, **kwargs: Any):
                return MockResponse({"balance": 2.5})

        def mock_account(data, address):
            return Account(balance=data.get("balance", 0), type="BTC", address=address)

        def mock_url(address):
            return f"https://example.com/{address}"

        queue = CoinyQueue()
        await queue.put((mock_account, mock_url, "test_address_123"))

        async with SuccessSession() as session:
            result = await balance_task(queue, session)
            expected = Account(balance=2.5, type="BTC", address="test_address_123")
            self.assertEqual(expected, result)


__all__ = ["ErrorHandlingTests"]
