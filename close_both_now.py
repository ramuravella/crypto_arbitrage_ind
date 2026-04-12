"""EMERGENCY: Close both LONG positions on both exchanges."""
import json, time, requests, hmac, hashlib
from cryptography.hazmat.primitives.asymmetric import ed25519

with open('config.json') as f:
    cfg = json.load(f)

CS_KEY = cfg['exchanges']['coinswitch']['api_key']
CS_SECRET = cfg['exchanges']['coinswitch']['api_secret']
CDCX_KEY = cfg['exchanges']['coindcx']['api_key']
CDCX_SECRET = cfg['exchanges']['coindcx']['api_secret']

def cs_post(path, payload):
    epoch = str(int(time.time() * 1000))
    msg = 'POST' + path + epoch
    priv = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(CS_SECRET))
    sig = priv.sign(msg.encode()).hex()
    hdrs = {'Content-Type': 'application/json', 'X-AUTH-APIKEY': CS_KEY,
            'X-AUTH-SIGNATURE': sig, 'X-AUTH-EPOCH': epoch}
    r = requests.post('https://coinswitch.co' + path, json=payload, headers=hdrs, timeout=10)
    return r.status_code, r.json() if r.ok else r.text

def cdcx_post(path, payload):
    payload['timestamp'] = int(time.time() * 1000)
    body = json.dumps(payload, separators=(',', ':'))
    sig = hmac.new(CDCX_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    hdrs = {'Content-Type': 'application/json', 'X-AUTH-APIKEY': CDCX_KEY, 'X-AUTH-SIGNATURE': sig}
    r = requests.post('https://api.coindcx.com' + path, data=body, headers=hdrs, timeout=10)
    return r.status_code, r.json() if r.ok else r.text

# === CLOSE COINSWITCH LONG (SELL, reduce_only) ===
print("=== Closing CoinSwitch LONG PIPPINUSDT (133 qty) ===")
code, data = cs_post("/trade/api/v2/futures/order", {
    "exchange": "EXCHANGE_2",
    "symbol": "PIPPINUSDT",
    "side": "SELL",
    "order_type": "MARKET",
    "quantity": 133,
    "reduce_only": True,
    "leverage": 5,
})
print(f"  Status: {code}")
print(f"  Response: {json.dumps(data, indent=2) if isinstance(data, dict) else data}")

# === CLOSE COINDCX LONG (sell, reduce_only, INR margin) ===
print("\n=== Closing CoinDCX LONG PIPPINUSDT (133 qty, INR margin) ===")
order = {
    "side": "sell",
    "pair": "B-PIPPIN_USDT",
    "order_type": "market_order",
    "total_quantity": 133.0,
    "leverage": 5,
    "margin_currency_short_name": "INR",
    "reduce_only": True,
    "notification": "no_notification",
    "time_in_force": "good_till_cancel",
    "hidden": False,
    "post_only": False,
}
code, data = cdcx_post("/exchange/v1/derivatives/futures/orders/create", {"order": order})
print(f"  Status: {code}")
print(f"  Response: {json.dumps(data, indent=2) if isinstance(data, dict) else data}")

# Wait and verify
print("\nWaiting 3s for fills...")
time.sleep(3)

# Check CoinSwitch
print("\n=== Verify CoinSwitch ===")
epoch = str(int(time.time() * 1000))
path = '/trade/api/v2/futures/positions?exchange=EXCHANGE_2'
msg = 'GET' + path + epoch
priv = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(CS_SECRET))
sig = priv.sign(msg.encode()).hex()
hdrs = {'Content-Type': 'application/json', 'X-AUTH-APIKEY': CS_KEY,
        'X-AUTH-SIGNATURE': sig, 'X-AUTH-EPOCH': epoch}
r = requests.get('https://coinswitch.co' + path, headers=hdrs, timeout=10)
if r.ok:
    positions = r.json().get('data', [])
    pippin = [p for p in positions if p.get('symbol') == 'PIPPINUSDT']
    if pippin:
        print(f"  STILL OPEN: qty={pippin[0].get('position_size')}")
    else:
        print("  CLOSED OK")
else:
    print(f"  ERROR: {r.status_code}")

# Check CoinDCX trades to confirm close
print("\n=== Verify CoinDCX (trade history) ===")
code, data = cdcx_post("/exchange/v1/derivatives/futures/trades", {"pair": "B-PIPPIN_USDT", "limit": 3})
print(f"  Status: {code}")
if isinstance(data, list):
    for t in data[:3]:
        print(f"    side={t.get('side')} qty={t.get('quantity')} price={t.get('price')}")
