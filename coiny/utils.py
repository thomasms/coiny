from collections import namedtuple
from typing import Any


class FunctionRegisterBorg:
    __shared_state = {"register": {}}

    def __init__(self):
        self.__dict__ = self.__shared_state


def _register(coin: Any, key: str, val: Any) -> None:
    borg = FunctionRegisterBorg()
    if coin not in borg.register:
        borg.register[coin] = {}
    borg.register[coin][key] = val


def register_url(coin: Any) -> Any:
    def decorator(func):
        _register(coin, "url_func", func)

    return decorator


def register_account(coin: Any) -> Any:
    def decorator(func):
        _register(coin, "account_func", func)

    return decorator


CoinPrice = namedtuple("CoinPrice", ["coin", "fiat", "rate"])
Fiat = namedtuple("Fiat", ["balance", "type"])
Account = namedtuple("Account", ["balance", "type", "address"])

NullFiat = Fiat(type="Null", balance=0)
NullCoinPrice = CoinPrice(coin="Null", fiat="Null", rate=0)
NullAccount = Account(type="Null", balance=0, address="")
