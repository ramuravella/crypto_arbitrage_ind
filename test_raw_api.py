"""
Raw API test — no connector abstractions, just direct HTTP calls.
Tests: CoinSwitch entry, CoinSwitch get_position, CoinDCX get_position, CoinDCX close.
"""
import json, time, requests, hmac, hashlib
from cryptography.hazmat.primitives.asymmetric import ed25519

with open('config.json') as f:
    cfg = json.load(f)

CS_KEY = cfg['exchanges']['coinswitch']['api_key']
CS_SECRET = cfg['exchanges']['coinswitch']['api_secret']
CDCX_KEY = cfg['exchanges']['coindcx']['api_key']
CDCX_SECRET = cfg['exchanges']['coindcx']['api_secret']

# ── CoinSwitch helpers ──
def cs_sign(method, path):
    epoch = str(int(time.time() * 1000))
    msg = method.upper() + path + epoch
    priv = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(CS_SECRET))
    sig = priv.sign(msg.encode()).hex()
    return {"Content-Type": "application/json", "X-AUTH-APIKEY": CS_KEY,
            "X-AUTH-SIGNATURE": sig, "X-AUTH-EPOCH": epoch}

def cs_get(path, params=None):
    from urllib.parse import urlencode
    qs = ("?" + urlencode(params)) if params else ""
    full = path + qs
    r = requests.get("https://coinswitch.co" + full, headers=cs_sign("GET", full), timeout=10)
    return r.status_code, r.json() if r.ok else r.text

def cs_post(path, payload):
    hdrs = cs_sign("POST", path)
    r = requests.post("https://coinswitch.co" + path, json=payload, headers=hdrs, timeout=10)
    return r.status_code, r.json() if r.ok else r.text

# ── CoinDCX helpers ──
def cdcx_signed_post(path, payload):
    payload['timestamp'] = int(time.time() * 1000)
    body = json.dumps(payload, separators=(',', ':'))
    sig = hmac.new(CDCX_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    hdrs = {"Content-Type": "application/json", "X-AUTH-APIKEY": CDCX_KEY, "X-AUTH-SIGNATURE": sig}
    r = requests.post("https://api.coindcx.com" + path, data=body, headers=hdrs, timeout=10)
    return r.status_code, r.json() if r.ok else r.text

print("=" * 60)
print("TEST 1: CoinSwitch — get all positions (raw)")
print("=" * 60)
code, data = cs_get("/trade/api/v2/futures/positions", {"exchange": "EXCHANGE_2"})
print(f"Status: {code}")
if isinstance(data, dict):
    positions = data.get('data', [])
    if isinstance(positions, list):
        print(f"Total positions: {len(positions)}")
        for p in positions:
            print(f"\n  Symbol: {p.get('symbol')}")
            print(f"  ALL KEYS: {list(p.keys())}")
            print(f"  Full data: {json.dumps(p, indent=4)}")
    else:
        print(f"Data type: {type(positions)}, value: {positions}")
else:
    print(f"Response: {data}")

print("\n" + "=" * 60)
print("TEST 2: CoinDCX — get all positions (raw)")
print("=" * 60)
code, data = cdcx_signed_post("/exchange/v1/derivatives/futures/positions", {})
print(f"Status: {code}")
if isinstance(data, list):
    print(f"Total positions: {len(data)}")
    for p in data:
        sym = p.get('pair', p.get('symbol', '?'))
        qty = p.get('quantity', p.get('total_quantity', p.get('active_pos', '?')))
        status = p.get('status', '?')
        print(f"\n  Symbol: {sym}, Qty: {qty}, Status: {status}")
        print(f"  ALL KEYS: {list(p.keys())}")
        # Print key fields
        for k in ['pair','symbol','side','quantity','total_quantity','active_pos',
                   'remaining_quantity','status','order_type','margin_currency_short_name',
                   'average_price','entry_price','pnl','realized_pnl']:
            if k in p:
                print(f"    {k}: {p[k]}")
elif isinstance(data, dict):
    print(f"Response keys: {list(data.keys())}")
    print(f"Response: {json.dumps(data, indent=2)[:500]}")
else:
    print(f"Response: {data}")

print("\n" + "=" * 60)
print("TEST 3: CoinSwitch — balance")
print("=" * 60)
code, data = cs_get("/trade/api/v2/futures/wallet_balance", {"exchange": "EXCHANGE_2"})
print(f"Status: {code}")
if isinstance(data, dict):
    print(json.dumps(data, indent=2)[:500])

print("\n" + "=" * 60)
print("TEST 4: CoinDCX — balance")
print("=" * 60)
code, data = cdcx_signed_post("/exchange/v1/derivatives/futures/wallet_balance", {})
print(f"Status: {code}")
if isinstance(data, dict) or isinstance(data, list):
    print(json.dumps(data, indent=2)[:500])
else:
    print(data[:500])
