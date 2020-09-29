  
from .wallet import Wallet

import requests
import logging
import json
import time
import urllib
import random


class Mcdex:
    logger = logging.getLogger()

    def __init__(self, api_url:str, market_id: str):
        self.api_url = api_url
        self.market_id = market_id
        self.wallet = None
        self.timeout = 5

    def set_wallet(self, private_key: str, public_key: str):
        self.wallet = Wallet(private_key, public_key)

    def generate_auth_headers(self, principal=None):
        timestamp = int(time.time() * 1000)
        signature = self.wallet.sign_hash(text=f"MAI-AUTHENTICATION@{timestamp}")
        result = {"Mai-Authentication": f"{self.wallet.address}#MAI-AUTHENTICATION@{timestamp}#{signature}"}
        if principal is not None:
            result["Mai-Principal"] = principal
        return result

    def api_request(self, http_method, url, params=None, headers=None):
        if http_method.lower() == "get":
            if headers is None:
                headers = {"content-type": "application/x-www-form-urlencoded"}
            else:
                headers["content-type"] = "application/x-www-form-urlencoded"

            if params is None:
                params = ""
            else:
                params = urllib.parse.urlencode(params)
            response = requests.get(url, params, timeout=self.timeout, headers=headers)
            code = response.status_code
            if code == 200:
                return response.json()
            else:
                return {"status": "fail", "code": code}
        elif http_method.lower() == "post":
            if headers is None:
                headers = {"content-type": "application/json"}
            else:
                headers["content-type"] = "application/json"

            if params is not None:
                params = json.dumps(params)
            response = requests.post(url, params, timeout=self.timeout, headers=headers)
            code = response.status_code
            if code == 200:
                return response.json()
            else:
                return {"status": "fail", "code": code}
        elif http_method.lower() == "delete":
            response = requests.delete(url, headers=headers)
            code = response.status_code
            if code == 200:
                return response.json()
            else:
                return {"status": "fail", "code": code}

    def get_balances(self):
        response_data = self.api_request("get", url=f"{self.api_url}/account/balances", params={"marketID": self.market_id}, headers=self.generate_auth_headers())
        print(f"[get balances response]{response_data}\n")

    def get_active_orders(self):
        response_data = self.api_request("get", url=f"{self.api_url}/orders", params={"status": "pending"}, headers=self.generate_auth_headers())
        print(f"[get active orders response]{response_data}\n")
        return response_data["data"]["orders"]

    def get_market_status(self):
        response_data = self.api_request("get", url=f"{self.api_url}/markets/{self.market_id}/status")
        print(f"[get market status response]{response_data}\n")
        index_price = response_data["data"]["lastIndex"]
        index_price = str(float(index_price) // 0.01 * 0.01)
        return index_price

    def build_unsigned_order(self, amount, price, side, order_type, expires, targetLeverage, isPostOnly=False):
        url = f"{self.api_url}/orders/build"
        headers = self.generate_auth_headers()
        params = {
            "amount": amount,
            "price": price,
            "side": side,
            "marketId": self.market_id,
            "orderType": order_type,
            "expires": expires,
            "targetLeverage": targetLeverage,
            "isPostOnly": isPostOnly
        }
        response_data = self.api_request('post', url=url, params=params, headers=headers)
        print(f"[build order response]{response_data}\n")
        return response_data["data"]["order"]

    def place_order(self, amount, order_type, price, side, expires, leverage):
        unsigned_order = self.build_unsigned_order(amount=amount, price=price, side=side,
                                            order_type=order_type, expires=expires,
                                            targetLeverage=leverage)
        order_id = unsigned_order["id"]
        signature = self.wallet.sign_hash(hexstr=order_id)
        signature = '0x' + signature[130:] + '0' * 62 + signature[2:130]
        params = {"orderID": order_id, "signature": signature, "method": 0}

        url = f"{self.api_url}/orders"
        response_data = self.api_request('post', url=url, params=params, headers=self.generate_auth_headers())
        print(f"[place order response]{response_data}\n")

    def cancel_all_orders(self):
        url = f"{self.api_url}/orders"
        response_data = self.api_request('delete', url=url, params={"marketID": self.market_id}, headers=self.generate_auth_headers())
        print(f"[cancel all orders response]{response_data}\n")

