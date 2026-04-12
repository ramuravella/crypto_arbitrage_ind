"""Dump full CoinDCX PIPPIN position data + try alternate endpoints."""
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

# 1. Standard positions — dump FULL PIPPIN record
print("=== 1. Standard positions endpoint ===")
code, data = signed_post("/exchange/v1/derivatives/futures/positions", {})
print(f"Status: {code}")
if isinstance(data, list):
    for p in data:
        if 'PIPPIN' in str(p.get('pair', '')).upper():
            print(f"\nFULL PIPPIN RECORD:")
            print(json.dumps(p, indent=2))

# 2. Try active_orders for PIPPIN
print("\n=== 2. Active orders ===")
for path in [
    "/exchange/v1/derivatives/futures/orders/active_orders",
    "/exchange/v1/derivatives/futures/orders/active_orders_by_pair",
]:
    code, data = signed_post(path, {"pair": "B-PIPPIN_USDT"})
    print(f"  {path}: status={code}")
    if isinstance(data, list):
        for o in data[:3]:
            print(f"    side={o.get('side')} qty={o.get('total_quantity')} status={o.get('status')} type={o.get('order_type')}")
    elif isinstance(data, dict):
        orders = data.get('orders', data.get('data', []))
        if isinstance(orders, list):
            for o in orders[:3]:
                print(f"    side={o.get('side')} qty={o.get('total_quantity')} status={o.get('status')}")
        else:
            print(f"    {str(data)[:300]}")
    else:
        print(f"    {str(data)[:300]}")

# 3. Trade history for PIPPIN
print("\n=== 3. Trade history ===")
for path in [
    "/exchange/v1/derivatives/futures/orders/trade_history",
    "/exchange/v1/derivatives/futures/trades",
]:
    code, data = signed_post(path, {"pair": "B-PIPPIN_USDT", "limit": 5})
    print(f"  {path}: status={code}")
    if isinstance(data, list):
        for t in data[:3]:
            print(f"    side={t.get('side')} qty={t.get('total_quantity',t.get('quantity'))} "
                  f"filled={t.get('filled_quantity')} price={t.get('price',t.get('avg_price'))} "
                  f"status={t.get('status')} time={t.get('created_at')}")
    elif isinstance(data, dict):
        trades = data.get('trades', data.get('data', []))
        if isinstance(trades, list):
            for t in trades[:3]:
                print(f"    side={t.get('side')} qty={t.get('quantity')} price={t.get('price')}")
        else:
            print(f"    {str(data)[:300]}")
    else:
        print(f"    {str(data)[:300]}")

# 4. Try the v2 endpoint
print("\n=== 4. v2 positions ===")
code, data = signed_post("/exchange/v2/derivatives/futures/positions", {})
print(f"  status={code}")
if isinstance(data, list):
    for p in data:
        if 'PIPPIN' in str(p.get('pair', p.get('symbol', ''))).upper():
            print(json.dumps(p, indent=2))
elif isinstance(data, dict):
    # Check if there's a data wrapper
    positions = data.get('data', data.get('positions', []))
    if isinstance(positions, list):
        for p in positions:
            if 'PIPPIN' in str(p.get('pair', p.get('symbol', ''))).upper():
                print(json.dumps(p, indent=2))
    else:
        print(f"  {str(data)[:300]}")
else:
    print(f"  {str(data)[:300]}")

# 5. Try querying by pair
print("\n=== 5. Position by pair ===")
code, data = signed_post("/exchange/v1/derivatives/futures/positions", {"pair": "B-PIPPIN_USDT"})
print(f"  status={code}")
if isinstance(data, list):
    for p in data:
        ap = p.get('active_pos', 0)
        pair = p.get('pair', '?')
        print(f"  pair={pair} active_pos={ap} margin={p.get('margin_currency_short_name')}")
        if 'PIPPIN' in pair.upper():
            print(json.dumps(p, indent=2))
elif isinstance(data, dict):
    print(f"  {str(data)[:300]}")
else:
    print(f"  {str(data)[:300]}")
