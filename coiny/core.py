from collections import defaultdict
import json
import asyncio
from aiohttp import ClientSession
from typing import Dict, List, Tuple

from coiny.utils import (
    FunctionRegisterBorg,
    NullAccount,
    NullCoinPrice,
    CoinPrice,
    Account,
)
from coiny.supported import *


def price_now_url(coin, currency="eur") -> Dict:
    """
    coin can be either: bitcoin, ethereum, dogecoin, ...
    currency can be either: usd, gbp, eur, ....
    """
    # response in form: {"dogecoin": {"eur": 0.210549}}
    return f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies={currency}"


async def price_task(work_queue) -> CoinPrice:
    rate = NullCoinPrice
    async with ClientSession() as session:
        while not work_queue.empty():
            coin, currency, url = await work_queue.get()
            async with session.get(url) as response:
                res = await response.json()
                if coin in res and currency in res[coin]:
                    rate = CoinPrice(fiat=currency, coin=coin, rate=res[coin][currency])
    return rate


async def balance_task(work_queue) -> Account:
    account = NullAccount
    async with ClientSession() as session:
        while not work_queue.empty():
            acc, template_url, address = await work_queue.get()
            url = template_url(address)
            async with session.get(url) as response:
                res = await response.json()
                account = acc(res, address)
    return account


async def get_prices(coins: List[str], currency: str = "eur") -> List[CoinPrice]:
    work_queue = asyncio.Queue()

    for coin in coins:
        await work_queue.put((coin, currency, price_now_url(coin, currency=currency)))

    # Run the tasks
    price_data = await asyncio.gather(
        *[asyncio.create_task(price_task(work_queue)) for _ in coins]
    )
    return price_data


async def get_accounts(addresses: List[Tuple[str, str]]) -> List[Account]:
    work_queue = asyncio.Queue()

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

    account_data = await asyncio.gather(
        *[asyncio.create_task(balance_task(work_queue)) for _ in ipts]
    )
    return account_data


async def check_accounts_async(
    coinsfile: str = "mycoins.json", currency: str = "eur"
) -> None:

    addresses = []
    with open(coinsfile, "rt") as jfile:
        data = json.load(jfile)
        # address must be the key for uniqueness
        for address, coin in data.items():
            addresses.append((coin, address))

    coins = set([x[0] for x in addresses])

    # CoinPrice = namedtuple("CoinPrice", ["coin", "fiat", "rate"])
    price_data = await get_prices(coins, currency=currency)

    # TODO: Filter out duplicate addresses
    # Account = namedtuple("Account", ["balance", "type", "address"])
    account_data = await get_accounts(addresses)

    # sum coins - we know the currency is EUR here,
    # but we should really set it in the portfolio
    portfolio = defaultdict(float)
    for account in account_data:
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
    asyncio.run(check_accounts_async(coinsfile=coinsfile, currency=currency))
