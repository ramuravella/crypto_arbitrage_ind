"""Try converting INR to USDT on CoinDCX"""
import json, sys
sys.path.insert(0, '.')

with open('config.json') as f:
    cfg = json.load(f)

from src.connectors.coindcx import CoinDCXConnector
cdcx = CoinDCXConnector(cfg)

# Try various conversion/transfer endpoints
endpoints_to_try = [
    ("POST", "/exchange/v1/derivatives/futures/wallets/convert", {"from_currency": "INR", "to_currency": "USDT", "amount": 200}),
    ("POST", "/exchange/v1/derivatives/futures/wallets/exchange", {"from_currency": "INR", "to_currency": "USDT", "amount": 200}),
    ("POST", "/exchange/v1/derivatives/futures/wallets/internal_transfer", {"from_currency": "INR", "to_currency": "USDT", "amount": 200}),
    ("POST", "/exchange/v1/derivatives/futures/wallets/swap", {"from": "INR", "to": "USDT", "amount": 200}),
    # Try transferring USDT from spot to futures
    ("POST", "/exchange/v1/derivatives/futures/wallets/transfer", {"transfer_type": "deposit", "amount": 2, "currency_short_name": "USDT"}),
]

for method, endpoint, payload in endpoints_to_try:
    try:
        if method == "POST":
            resp = cdcx._signed_post(endpoint, payload)
        else:
            resp = cdcx._signed_get(endpoint)
        print(f"  {endpoint}: {json.dumps(resp, indent=2, default=str)[:300]}")
    except Exception as e:
        error_str = str(e)
        # Check if it's a 400 with useful message
        if '400' in error_str or '422' in error_str:
            print(f"  {endpoint}: {error_str[:200]}")
        else:
            print(f"  {endpoint}: {error_str[:100]}")

# Check spot balance for USDT
print("\n=== Check Spot Balances ===")
try:
    spot = cdcx._signed_post("/exchange/v1/users/balances", {})
    if isinstance(spot, list):
        for b in spot:
            curr = b.get('currency', b.get('currency_short_name', ''))
            balance = b.get('balance', 0)
            if float(balance or 0) > 0 or 'USDT' in str(curr).upper() or 'INR' in str(curr).upper():
                print(f"  {curr}: balance={balance}, locked={b.get('locked_balance', 0)}")
    else:
        print(f"  Response: {json.dumps(spot, default=str)[:500]}")
except Exception as e:
    print(f"  ERROR: {e}")
