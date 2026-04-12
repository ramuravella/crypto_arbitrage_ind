"""
Test CoinDCX API endpoints to find the correct positions endpoint.
"""
import json
import time
import hmac
import hashlib
import requests

with open("config.json") as f:
    config = json.load(f)

api_key = config['exchanges']['coindcx']['api_key']
api_secret = config['exchanges']['coindcx']['api_secret']

def signed_post(path, payload=None):
    if payload is None:
        payload = {}
    payload['timestamp'] = int(time.time() * 1000)
    json_body = json.dumps(payload, separators=(',', ':'))
    sig = hmac.new(api_secret.encode(), json_body.encode(), hashlib.sha256).hexdigest()
    headers = {'Content-Type': 'application/json',
               'X-AUTH-APIKEY': api_key, 'X-AUTH-SIGNATURE': sig}
    r = requests.post(f"https://api.coindcx.com{path}", data=json_body, headers=headers, timeout=10)
    return r.status_code, r.text[:500]

def signed_get(path, payload=None):
    if payload is None:
        payload = {}
    payload['timestamp'] = int(time.time() * 1000)
    json_body = json.dumps(payload, separators=(',', ':'))
    sig = hmac.new(api_secret.encode(), json_body.encode(), hashlib.sha256).hexdigest()
    headers = {'Content-Type': 'application/json',
               'X-AUTH-APIKEY': api_key, 'X-AUTH-SIGNATURE': sig}
    r = requests.get(f"https://api.coindcx.com{path}", data=json_body, headers=headers, timeout=10)
    return r.status_code, r.text[:500]

# Test all possible position endpoints
endpoints = [
    ("POST", "/exchange/v1/derivatives/positions"),
    ("POST", "/exchange/v1/derivatives/futures/positions"),
    ("POST", "/exchange/v1/derivatives/futures/data/positions"),
    ("GET",  "/exchange/v1/derivatives/futures/positions"),
    ("GET",  "/exchange/v1/derivatives/futures/data/positions"),
    ("POST", "/exchange/v1/derivatives/futures/positions/active"),
    ("POST", "/exchange/v1/derivatives/futures/data/active_positions"),
    ("GET",  "/exchange/v1/derivatives/positions"),
]

print("Testing CoinDCX position endpoints:\n")
for method, path in endpoints:
    try:
        if method == "POST":
            code, text = signed_post(path)
        else:
            code, text = signed_get(path)
        status = "OK" if code == 200 else f"FAIL({code})"
        print(f"  {method} {path}")
        print(f"    -> {status}: {text[:200]}")
        print()
    except Exception as e:
        print(f"  {method} {path} -> ERROR: {e}")
        print()

# Also test the close/create order endpoints
print("\n\nTesting CoinDCX order endpoints:\n")
order_endpoints = [
    ("POST", "/exchange/v1/derivatives/futures/orders/create"),
    ("POST", "/exchange/v1/derivatives/futures/orders"),
    ("POST", "/exchange/v1/derivatives/orders/create"),
]
for method, path in order_endpoints:
    try:
        code, text = signed_post(path, {"order": {"side": "test"}})
        status = "OK" if code == 200 else f"FAIL({code})"
        print(f"  {method} {path}")
        print(f"    -> {status}: {text[:200]}")
        print()
    except Exception as e:
        print(f"  {method} {path} -> ERROR: {e}")
        print()

# Test wallet endpoints for reference
print("\nTesting wallet/balance endpoints:\n")
wallet_endpoints = [
    ("GET",  "/exchange/v1/derivatives/futures/wallets"),
    ("POST", "/exchange/v1/derivatives/futures/wallets"),
    ("POST", "/exchange/v1/derivatives/futures/data/wallet_details"),
]
for method, path in wallet_endpoints:
    try:
        if method == "POST":
            code, text = signed_post(path)
        else:
            code, text = signed_get(path)
        status = "OK" if code == 200 else f"FAIL({code})"
        print(f"  {method} {path}")
        print(f"    -> {status}: {text[:200]}")
        print()
    except Exception as e:
        print(f"  {method} {path} -> ERROR: {e}")
        print()
