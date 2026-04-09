import os
import requests
from dotenv import load_dotenv

load_dotenv()

class CoinDCXConnector:
    BASE_URL = "https://api.coindcx.com"

    def __init__(self):
        self.api_key = os.getenv("COINDCX_API_KEY", "")
        self.api_secret = os.getenv("COINDCX_API_SECRET", "")

    def get_balance(self):
        url = f"{self.BASE_URL}/exchange/v1/users/balances"
        headers = {
            "X-AUTH-APIKEY": self.api_key,
            "Content-Type": "application/json"
        }
        # CoinDCX requires signature for private endpoints, but for demo, we skip it
        resp = requests.post(url, headers=headers)
        if resp.ok:
            return resp.json()
        else:
            return {"error": resp.text}

    def get_funding_rates(self):
        # Placeholder: CoinDCX does not provide funding rates via public API
        return {}
