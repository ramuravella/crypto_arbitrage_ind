"""Check full CoinDCX wallet details - INR and USDT"""
import json, sys
sys.path.insert(0, '.')

with open('config.json') as f:
    cfg = json.load(f)

from src.connectors.coindcx import CoinDCXConnector
cdcx = CoinDCXConnector(cfg)

print("=== Full CoinDCX Wallets ===")
wallets = cdcx._signed_get("/exchange/v1/derivatives/futures/wallets")
for w in wallets:
    currency = w.get('currency_short_name', '?')
    balance = w.get('balance', 0)
    locked = w.get('locked_balance', 0)
    avail = float(balance or 0) - float(locked or 0)
    print(f"  {currency}: balance={balance}, locked={locked}, available={avail}")
    print(f"    Full: {json.dumps(w, indent=2, default=str)}")

# Check for pending/unfilled orders
print("\n=== Pending Orders ===")
endpoints = [
    "/exchange/v1/derivatives/futures/orders/active_orders",
    "/exchange/v1/derivatives/futures/orders/active_orders_count",
    "/exchange/v1/derivatives/futures/orders",
]
for ep in endpoints:
    try:
        resp = cdcx._signed_post(ep, {})
        print(f"  {ep}: {json.dumps(resp, indent=2, default=str)[:500]}")
    except Exception as e:
        try:
            resp = cdcx._signed_get(ep)
            print(f"  {ep} (GET): {json.dumps(resp, indent=2, default=str)[:500]}")
        except Exception as e2:
            print(f"  {ep}: ERROR ({e})")

# Try GET for active orders
print("\n=== Try active orders endpoint variants ===")
try:
    resp = cdcx._signed_post("/exchange/v1/derivatives/futures/orders/active_orders", 
                              {"pair": "B-PIPPIN_USDT"})
    print(f"  Active orders for PIPPIN: {json.dumps(resp, indent=2, default=str)[:500]}")
except:
    pass

try:
    resp = cdcx._signed_post("/exchange/v1/derivatives/futures/orders/active", {})
    print(f"  /active: {json.dumps(resp, indent=2, default=str)[:500]}")
except:
    pass
