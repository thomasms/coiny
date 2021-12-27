from typing import Dict, Union

from coiny.utils import register_account, register_url, Account
from coiny.supported import ETH


@register_url(ETH)
def eth_address_url(address: str) -> str:
    return f"https://api.blockcypher.com/v1/eth/main/addrs/{address}/balance"


@register_account(ETH)
def eth_account(data: Dict, address: str = None) -> Union[Account, None]:
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


__all__ = ["eth_address_url", "eth_account"]
