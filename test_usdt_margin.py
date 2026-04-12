"""Test USDT-margin order on CoinDCX (uses INR wallet with auto-conversion)."""
import json, time, requests, hmac, hashlib

with open('config.json') as f:
    cfg = json.load(f)

KEY = cfg['exchanges']['coindcx']['api_key']
SECRET = cfg['exchanges']['coindcx']['api_secret']

def cdcx_post(path, payload):
    payload['timestamp'] = int(time.time() * 1000)
    body = json.dumps(payload, separators=(',', ':'))
    sig = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    hdrs = {'Content-Type': 'application/json', 'X-AUTH-APIKEY': KEY, 'X-AUTH-SIGNATURE': sig}
    r = requests.post('https://api.coindcx.com' + path, data=body, headers=hdrs, timeout=10)
    return r.status_code, r.json() if r.ok else r.text

# Step 1: Open a tiny LONG with USDT margin
print("=== OPEN: BUY PIPPINUSDT 133 qty, USDT margin, 5x ===")
order = {
    "side": "buy",
    "pair": "B-PIPPIN_USDT",
    "order_type": "market_order",
    "total_quantity": 133.0,
    "leverage": 5,
    "margin_currency_short_name": "USDT",
    "notification": "no_notification",
    "time_in_force": "good_till_cancel",
    "hidden": False,
    "post_only": False,
}
code, data = cdcx_post("/exchange/v1/derivatives/futures/orders/create", {"order": order})
print(f"  Status: {code}")
if isinstance(data, list) and data:
    d = data[0]
    print(f"  id={d.get('id')}")
    print(f"  side={d.get('side')}, qty={d.get('total_quantity')}, margin={d.get('margin_currency_short_name')}")
    print(f"  settlement_conversion={d.get('settlement_currency_conversion_price')}")
    print(f"  status={d.get('status')}")
elif isinstance(data, dict):
    print(f"  {json.dumps(data, indent=2)[:500]}")
else:
    print(f"  {data}")

if code != 200:
    print("\n  USDT margin order FAILED — cannot proceed")
    exit(1)

# Step 2: Wait and check position
print("\n=== CHECK POSITION (1s delay) ===")
time.sleep(1)
code, positions = cdcx_post("/exchange/v1/derivatives/futures/positions", {})
print(f"  Status: {code}")
if isinstance(positions, list):
    for p in positions:
        if 'PIPPIN' in p.get('pair', '').upper():
            ap = p.get('active_pos', 0)
            margin = p.get('margin_currency_short_name', '?')
            avg = p.get('avg_price', 0)
            print(f"  PIPPIN: active_pos={ap}, margin={margin}, avg_price={avg}")
            if float(ap) != 0:
                print(f"  >>> POSITION DETECTED via API! <<<")
            else:
                print(f"  >>> active_pos still 0 — position NOT visible <<<")

# Step 3: Close immediately
print("\n=== CLOSE: SELL PIPPINUSDT 133 qty ===")
close_order = {
    "side": "sell",
    "pair": "B-PIPPIN_USDT",
    "order_type": "market_order",
    "total_quantity": 133.0,
    "leverage": 5,
    "margin_currency_short_name": "USDT",
    "notification": "no_notification",
    "time_in_force": "good_till_cancel",
    "hidden": False,
    "post_only": False,
}
code, data = cdcx_post("/exchange/v1/derivatives/futures/orders/create", {"order": close_order})
print(f"  Status: {code}")
if isinstance(data, list) and data:
    print(f"  status={data[0].get('status')}, margin={data[0].get('margin_currency_short_name')}")
elif isinstance(data, dict):
    print(f"  {json.dumps(data, indent=2)[:300]}")
else:
    print(f"  {data}")

# Step 4: Verify closed
time.sleep(1)
code, positions = cdcx_post("/exchange/v1/derivatives/futures/positions", {})
if isinstance(positions, list):
    for p in positions:
        if 'PIPPIN' in p.get('pair', '').upper():
            ap = p.get('active_pos', 0)
            print(f"\n  After close: PIPPIN active_pos={ap}")
