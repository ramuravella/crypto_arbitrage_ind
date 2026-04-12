"""Close CoinDCX LONG — no reduce_only (not supported with market orders)."""
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

# Close LONG = SELL without reduce_only
print("=== Closing CoinDCX LONG PIPPINUSDT (133 qty, INR margin, no reduce_only) ===")
order = {
    "side": "sell",
    "pair": "B-PIPPIN_USDT",
    "order_type": "market_order",
    "total_quantity": 133.0,
    "leverage": 5,
    "margin_currency_short_name": "INR",
    "notification": "no_notification",
    "time_in_force": "good_till_cancel",
    "hidden": False,
    "post_only": False,
}
code, data = cdcx_post("/exchange/v1/derivatives/futures/orders/create", {"order": order})
print(f"  Status: {code}")
print(f"  Response: {json.dumps(data, indent=2) if isinstance(data, dict) else data}")

time.sleep(2)

# Check trades
print("\n=== Recent trades ===")
code, data = cdcx_post("/exchange/v1/derivatives/futures/trades", {"pair": "B-PIPPIN_USDT", "limit": 5})
if isinstance(data, list):
    for t in data[:5]:
        print(f"  side={t.get('side')} qty={t.get('quantity')} price={t.get('price')}")
