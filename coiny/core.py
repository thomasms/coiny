import asyncio
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from aiohttp import ClientSession, ClientError, ClientResponseError

from coiny.supported import *
from coiny.utils import (
    Account,
    CoinPrice,
    FunctionRegisterBorg,
    NullAccount,
    NullCoinPrice,
)

logger = logging.getLogger(__name__)

CoinyQueue: asyncio.Queue = asyncio.Queue
CoinySession: ClientSession = ClientSession


def price_now_url(coin, currency="eur") -> Dict:
    """
    coin can be either: bitcoin, ethereum, dogecoin, ...
    currency can be either: usd, gbp, eur, ....
    """
    # response in form: {"dogecoin": {"eur": 0.210549}}
    return f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies={currency}"


async def price_task(work_queue: Any, session: CoinySession) -> CoinPrice:
    rate = NullCoinPrice
    while not work_queue.empty():
        coin, currency, url = await work_queue.get()
        try:
            logger.debug(f"Fetching price for {coin} in {currency} from {url}")
            async with session.get(url) as response:
                response.raise_for_status()
                res = await response.json()
                if coin in res and currency in res[coin]:
                    rate = CoinPrice(fiat=currency, coin=coin, rate=res[coin][currency])
                    logger.debug(f"Successfully fetched price for {coin}: {rate.rate} {currency}")
                else:
                    logger.warning(f"Price data for {coin}/{currency} not found in API response")
        except ClientResponseError as e:
            logger.error(f"HTTP error fetching price for {coin}: {e.status} {e.message} - URL: {url}")
        except ClientError as e:
            logger.error(f"Connection error fetching price for {coin}: {str(e)} - URL: {url}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching price for {coin} from {url}")
        except Exception as e:
            logger.error(f"Unexpected error fetching price for {coin}: {type(e).__name__}: {str(e)} - URL: {url}")
    return rate


async def balance_task(work_queue: Any, session: CoinySession) -> Account:
    account = NullAccount
    while not work_queue.empty():
        acc, template_url, address = await work_queue.get()
        url = template_url(address)
        try:
            logger.debug(f"Fetching balance for address {address} from {url}")
            async with session.get(url) as response:
                response.raise_for_status()
                res = await response.json()
                account = acc(res, address)
                logger.debug(f"Successfully fetched balance for {address}: {account.balance}")
        except ClientResponseError as e:
            logger.error(f"HTTP error fetching balance for {address}: {e.status} {e.message} - URL: {url}")
        except ClientError as e:
            logger.error(f"Connection error fetching balance for {address}: {str(e)} - URL: {url}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching balance for {address} from {url}")
        except Exception as e:
            logger.error(f"Unexpected error fetching balance for {address}: {type(e).__name__}: {str(e)} - URL: {url}")
    return account


async def get_prices(coins: List[str], currency: str = "eur") -> List[CoinPrice]:
    work_queue = CoinyQueue()

    for coin in coins:
        await work_queue.put((coin, currency, price_now_url(coin, currency=currency)))

    async with CoinySession() as session:
        price_data = await asyncio.gather(
            *[asyncio.create_task(price_task(work_queue, session)) for _ in coins]
        )
        return price_data


async def get_accounts(addresses: List[Tuple[str, str]]) -> List[Account]:
    work_queue = CoinyQueue()

    borg = FunctionRegisterBorg()
    ipts = [
        (
            borg.register[coin]["account_func"],
            borg.register[coin]["url_func"],
            address,
        )
        for (coin, address) in addresses
    ]
    for acc, url, address in ipts:
        await work_queue.put((acc, url, address))

    async with CoinySession() as session:
        try:
            logger.info(f"Fetching account data for {len(ipts)} addresses")
            account_data = await asyncio.gather(
                *[asyncio.create_task(balance_task(work_queue, session)) for _ in ipts]
            )
            logger.info(f"Successfully fetched {len([a for a in account_data if isinstance(a, Account)])} accounts")
        except Exception as e:
            logger.error(f"Critical error in get_accounts: {type(e).__name__}: {str(e)}")
            account_data = [NullAccount]
        return account_data


def read_config(configfile: str) -> Dict:
    data = {}
    with open(configfile, "rt") as jfile:
        data = json.load(jfile)
    return data


async def check_accounts_async(coin_data: Dict, currency: str = "eur") -> None:
    # address must be the key for uniqueness
    coins_and_addresses = [(coin, address) for address, coin in coin_data.items()]
    unique_coins = set([x[0] for x in coins_and_addresses])

    # CoinPrice = namedtuple("CoinPrice", ["coin", "fiat", "rate"])
    price_data = await get_prices(unique_coins, currency=currency)

    # TODO: Filter out duplicate addresses
    # Account = namedtuple("Account", ["balance", "type", "address"])
    account_data = await get_accounts(coins_and_addresses)

    # sum coins - we know the currency is EUR here,
    # but we should really set it in the portfolio
    portfolio = defaultdict(float)
    for account in account_data:
        if isinstance(account, Account):
            rates = [price.rate for price in price_data if price.coin == account.type]
            rate = rates[0] if rates else 0.0
            portfolio[account.type] += rate * account.balance

    # print(portfolio)

    total = sum([v for _, v in portfolio.items()])
    for k, v in portfolio.items():
        print(f"{k:<14} = {v:10.2f} {currency} ({v*100/total:.2f}%)")

    print("=".join([""] * 40))
    print(f"{'total':<14} = {total:10.2f} {currency} ({100:.2f}%)")


def check_accounts(coinsfile: str = "mycoins.json", currency: str = "eur") -> None:
    coin_data = read_config(coinsfile)
    asyncio.run(check_accounts_async(coin_data, currency=currency))
