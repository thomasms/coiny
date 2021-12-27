from typing import Dict, Union

from coiny.utils import register_account, register_url, Account
from coiny.supported import BTC


@register_url(BTC)
def btc_address_url(address: str) -> str:
    return f"https://blockchain.info/balance?active={address}"


@register_account(BTC)
def btc_account(data: Dict, address: str = None) -> Union[Account, None]:
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


__all__ = ["btc_address_url", "btc_account"]
