from collections import namedtuple, defaultdict
import json
import asyncio
from aiohttp import ClientSession

# coins
DOGE = "dogecoin"
ETH = "ethereum"
BTC = "bitcoin"

CoinPrice = namedtuple("CoinPrice", ["coin", "fiat", "rate"])
Fiat = namedtuple("Fiat", ["balance", "type"])
Account = namedtuple("Account", ["balance", "type", "address"])

NullFiat = Fiat(type="Null", balance=0)
NullCoinPrice = CoinPrice(coin="Null", fiat="Null", rate=0)
NullAccount = Account(type="Null", balance=0, address="")


class FunctionRegisterBorg:
    __shared_state = {"register": {}}

    def __init__(self):
        self.__dict__ = self.__shared_state


def _register(coin, key, val):
    borg = FunctionRegisterBorg()
    if coin not in borg.register:
        borg.register[coin] = {}
    borg.register[coin][key] = val


def register_url(coin):
    def decorator(func):
        _register(coin, "url_func", func)

    return decorator


def register_account(coin):
    def decorator(func):
        _register(coin, "account_func", func)

    return decorator


def price_now_url(coin, currency="eur"):
    """
    coin can be either: bitcoin, ethereum, dogecoin, ...
    currency can be either: usd, gbp, eur, ....
    """
    # response in form: {"dogecoin": {"eur": 0.210549}}
    return f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies={currency}"


@register_url(BTC)
def btc_address_url(address):
    return f"https://blockchain.info/balance?active={address}"


@register_account(BTC)
def btc_account(data, address=None):
    """Balance in sats (1e-8 btc)"""
    # expects in form:
    # {
    #    "1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ": {
    #     "final_balance": 11560362131675,
    #     "n_tx": 403,
    #     "total_received": 17925390781238
    #     }
    # }
    an = list(data.keys()).pop()
    ndata = data[an]
    if "final_balance" in ndata:
        if address:
            assert an == address
        return Account(type=BTC, balance=ndata["final_balance"] * 1e-8, address=an)
    return None


@register_url(DOGE)
def doge_address_url(address):
    return f"https://dogechain.info/api/v1/address/balance/{address}"


@register_account(DOGE)
def doge_account(data, address=None):
    # expects in form:
    # {
    #     'balance': '123456.789',
    #     'success': 1
    # }
    if "balance" in data and "success" in data and data["success"] == 1:
        addr = ""
        if address:
            addr = address
        return Account(type=DOGE, balance=float(data["balance"]), address=addr)
    return None


@register_url(ETH)
def eth_address_url(address):
    return f"https://api.blockcypher.com/v1/eth/main/addrs/{address}/balance"


@register_account(ETH)
def eth_account(data, address=None):
    """Balance in wei (1e-18 eth)"""
    # expects in form:
    # {
    # "address": "0xAB8B9f94D369BB26FAF61968D9a96dC1C2863eF9",
    # "total_received": 362685170000000000,
    # "total_sent": 0,
    # "balance": 362685170000000000,
    # "unconfirmed_balance": 0,
    # "final_balance": 362685170000000000,
    # "n_tx": 3,
    # "unconfirmed_n_tx": 0,
    # "final_n_tx": 3
    # }
    if "final_balance" in data and "address" in data:
        if address:
            assert data["address"] == address
        return Account(
            type=ETH,
            balance=data["final_balance"] * 1e-18,
            address=data["address"],
        )
    return None


async def price_task(work_queue):
    rate = NullCoinPrice
    async with ClientSession() as session:
        while not work_queue.empty():
            coin, currency, url = await work_queue.get()
            async with session.get(url) as response:
                res = await response.json()
                if coin in res and currency in res[coin]:
                    rate = CoinPrice(fiat=currency, coin=coin, rate=res[coin][currency])
    return rate


async def balance_task(work_queue):
    account = NullAccount
    async with ClientSession() as session:
        while not work_queue.empty():
            acc, template_url, address = await work_queue.get()
            url = template_url(address)
            async with session.get(url) as response:
                res = await response.json()
                account = acc(res, address)
    return account


async def get_prices(coins, currency="eur"):
    work_queue = asyncio.Queue()

    for coin in coins:
        await work_queue.put((coin, currency, price_now_url(coin, currency=currency)))

    # Run the tasks
    price_data = await asyncio.gather(
        *[asyncio.create_task(price_task(work_queue)) for _ in coins]
    )
    return price_data


async def get_accounts(addresses):
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


async def check_accounts_async(coinsfile="mycoins.json", currency="eur"):

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


def check_accounts(coinsfile="mycoins.json", currency="eur"):
    asyncio.run(check_accounts_async(coinsfile=coinsfile, currency=currency))

