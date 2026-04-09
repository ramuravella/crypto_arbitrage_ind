import os
import requests
import time
import hmac
import hashlib
from dotenv import load_dotenv

load_dotenv()

class DeltaConnector:
    BASE_URL = "https://api.india.delta.exchange/v2"

    def __init__(self):
        self.api_key = os.getenv("DELTA_API_KEY", "")
        self.api_secret = os.getenv("DELTA_API_SECRET", "")

    def _headers(self, method, path, query_string='', payload=''):
        timestamp = str(int(time.time()))
        signature_data = method + timestamp + path + query_string + payload
        signature = hmac.new(self.api_secret.encode(), signature_data.encode(), hashlib.sha256).hexdigest()
        return {
            "api-key": self.api_key,
            "timestamp": timestamp,
            "signature": signature,
            "User-Agent": "python-rest-client",
            "Content-Type": "application/json"
        }

    def get_balance(self):
        path = "/wallet/balances"
        url = self.BASE_URL + path
        headers = self._headers('GET', path)
        resp = requests.get(url, headers=headers)
        if resp.ok:
            return resp.json()
        else:
            return {"error": resp.text}

    def get_funding_rates(self):
        path = "/products"
        url = self.BASE_URL + path
        headers = self._headers('GET', path)
        resp = requests.get(url, headers=headers)
        if resp.ok:
            return resp.json()
        else:
            return {"error": resp.text}
