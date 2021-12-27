from typing import Dict, Union

from coiny.utils import register_account, register_url, Account
from coiny.supported import DOGE


@register_url(DOGE)
def doge_address_url(address: str) -> str:
    return f"https://dogechain.info/api/v1/address/balance/{address}"


@register_account(DOGE)
def doge_account(data: Dict, address=None) -> Union[Account, None]:
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


__all__ = ["doge_address_url", "doge_account"]
