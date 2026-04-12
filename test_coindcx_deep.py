"""
Test CoinDCX positions with different margin_currency filters.
Hypothesis: INR-margined positions are separate from USDT ones.
"""
import json, time, requests, hmac, hashlib

with open('config.json') as f:
    cfg = json.load(f)

KEY = cfg['exchanges']['coindcx']['api_key']
SECRET = cfg['exchanges']['coindcx']['api_secret']

def signed_post(path, payload):
    payload['timestamp'] = int(time.time() * 1000)
    body = json.dumps(payload, separators=(',', ':'))
    sig = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    hdrs = {"Content-Type": "application/json", "X-AUTH-APIKEY": KEY, "X-AUTH-SIGNATURE": sig}
    r = requests.post("https://api.coindcx.com" + path, data=body, headers=hdrs, timeout=10)
    return r.status_code, r.json() if r.ok else r.text

# Test 1: No filter
print("=" * 60)
print("TEST 1: Positions — no filter")
code, data = signed_post("/exchange/v1/derivatives/futures/positions", {})
print(f"Status: {code}, Count: {len(data) if isinstance(data, list) else '?'}")
if isinstance(data, list):
    for p in data:
        if float(p.get('active_pos', 0)) != 0:
            print(f"  ACTIVE: {p.get('pair')} active_pos={p['active_pos']} margin={p.get('margin_currency_short_name')}")

# Test 2: Filter by margin_currency_short_name=INR
print("\n" + "=" * 60)
print("TEST 2: Positions — margin_currency_short_name=INR")
code, data = signed_post("/exchange/v1/derivatives/futures/positions", {"margin_currency_short_name": "INR"})
print(f"Status: {code}")
if isinstance(data, list):
    print(f"Count: {len(data)}")
    for p in data:
        print(f"  {p.get('pair')} active_pos={p.get('active_pos')} margin={p.get('margin_currency_short_name')}")
elif isinstance(data, dict):
    print(json.dumps(data, indent=2)[:300])
else:
    print(data[:300])

# Test 3: Active orders — maybe orders are pending?
print("\n" + "=" * 60)
print("TEST 3: Active orders")
code, data = signed_post("/exchange/v1/derivatives/futures/orders/active_orders", {})
print(f"Status: {code}")
if isinstance(data, list):
    print(f"Count: {len(data)}")
    for o in data[:5]:
        print(f"  {o.get('pair')} side={o.get('side')} qty={o.get('total_quantity')} status={o.get('status')}")
elif isinstance(data, dict):
    print(json.dumps(data, indent=2)[:300])
else:
    print(str(data)[:300])

# Test 4: Order history — recent orders
print("\n" + "=" * 60)
print("TEST 4: Recent order history")
code, data = signed_post("/exchange/v1/derivatives/futures/orders/trade_history", {"limit": 5})
print(f"Status: {code}")
if isinstance(data, list):
    print(f"Count: {len(data)}")
    for o in data[:5]:
        print(f"  {o.get('pair')} side={o.get('side')} qty={o.get('total_quantity')} filled={o.get('filled_quantity')} "
              f"status={o.get('status')} margin={o.get('margin_currency_short_name')} time={o.get('created_at')}")
        print(f"    ALL KEYS: {list(o.keys())}")
elif isinstance(data, dict):
    print(json.dumps(data, indent=2)[:500])
else:
    print(str(data)[:500])

# Test 5: Wallet balance — check ALL methods
print("\n" + "=" * 60)
print("TEST 5: Wallet/Balance endpoints")
for path in [
    "/exchange/v1/users/balances",
    "/exchange/v1/derivatives/futures/wallet_details",
]:
    code, data = signed_post(path, {})
    print(f"\n  {path}: Status {code}")
    if isinstance(data, list):
        for b in data[:3]:
            cur = b.get('currency', b.get('symbol', '?'))
            bal = b.get('balance', b.get('available_balance', b.get('total_balance', '?')))
            print(f"    {cur}: {bal}")
    elif isinstance(data, dict):
        print(f"    {json.dumps(data, indent=2)[:200]}")
    else:
        print(f"    {str(data)[:200]}")
