from typing import Dict, Union

from coiny.utils import register_account, register_url, Account
from coiny.supported import HTR


@register_url(HTR)
def htr_address_url(address: str) -> str:
    return f"https://explorer-service.hathor.network/node_api/address_balance?address={address}"


@register_account(HTR)
def htr_account(data: Dict, address: str = None) -> Union[Account, None]:
    """Balance in 10mHTR"""
    # expects in form:
    # {
    # "success": true,
    # "total_transactions": 13,
    # "tokens_data": {
    #     "00": {
    #     "received": 68122,
    #     "spent": 0,
    #     "name": "Hathor",
    #     "symbol": "HTR"
    #     }
    # }
    # }
    if "success" in data and data["success"] and "tokens_data" in data:
        if "00" in data["tokens_data"]:
            addr = ""
            if address:
                addr = address
            balance = (
                data["tokens_data"]["00"]["received"]
                - data["tokens_data"]["00"]["spent"]
            ) * 1e-2
            return Account(balance=balance, type=HTR, address=addr)
    return None


__all__ = ["htr_address_url", "htr_account"]
