"""Quick test: CoinDCX positions + CoinSwitch exchange param"""
import json, time, hmac, hashlib, requests
from cryptography.hazmat.primitives.asymmetric import ed25519
import urllib.parse

with open("config.json") as f:
    config = json.load(f)

# ── CoinDCX: full positions data ──
api_key = config['exchanges']['coindcx']['api_key']
api_secret = config['exchanges']['coindcx']['api_secret']

payload = {"timestamp": int(time.time() * 1000)}
json_body = json.dumps(payload, separators=(',', ':'))
sig = hmac.new(api_secret.encode(), json_body.encode(), hashlib.sha256).hexdigest()
headers = {'Content-Type': 'application/json', 'X-AUTH-APIKEY': api_key, 'X-AUTH-SIGNATURE': sig}
r = requests.post("https://api.coindcx.com/exchange/v1/derivatives/futures/positions",
                   data=json_body, headers=headers, timeout=10)
print("=== CoinDCX Positions (correct endpoint) ===")
positions = r.json()
for p in positions:
    qty = float(p.get('active_pos', 0) or 0)
    if qty != 0 or True:  # Show all for debug
        print(f"\n  {p.get('pair','?')}")
        print(f"    active_pos={p.get('active_pos')} avg_price={p.get('avg_price')}")
        print(f"    locked_margin={p.get('locked_margin')} liq_price={p.get('liquidation_price')}")
        print(f"    leverage={p.get('leverage')} side={p.get('side','?')}")
        print(f"    ALL KEYS: {list(p.keys())}")
    if len([pp for pp in positions if float(pp.get('active_pos',0))!=0]) == 0 and positions.index(p) > 2:
        break

# Show only positions with active_pos != 0
active = [p for p in positions if float(p.get('active_pos', 0) or 0) != 0]
print(f"\n  ACTIVE POSITIONS: {len(active)} out of {len(positions)} total")
for p in active:
    print(f"    {p.get('pair')} active_pos={p.get('active_pos')} side={p.get('side','?')}")

# ── CoinSwitch: Test exchange in body vs query for various endpoints ──
cs_key = config['exchanges']['coinswitch']['api_key']
cs_secret = config['exchanges']['coinswitch']['api_secret']

def cs_sign(method, path):
    epoch = str(int(time.time() * 1000))
    msg = method.upper() + path + epoch
    priv = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(cs_secret))
    sig = priv.sign(msg.encode()).hex()
    return {
        "Content-Type": "application/json",
        "X-AUTH-APIKEY": cs_key,
        "X-AUTH-SIGNATURE": sig,
        "X-AUTH-EPOCH": epoch,
    }

def cs_post(path, payload, params=None):
    qs = ("?" + urllib.parse.urlencode(params)) if params else ""
    full = path + qs
    h = cs_sign("POST", full)
    r = requests.post(f"https://coinswitch.co{full}", json=payload, headers=h, timeout=10)
    return r.status_code, r.text[:300]

print("\n\n=== CoinSwitch: exchange param testing ===")

# Test leverage endpoint with exchange in BODY
print("\n  Leverage with exchange in BODY:")
code, text = cs_post("/trade/api/v2/futures/leverage",
    {"exchange": "EXCHANGE_2", "symbol": "BTCUSDT", "leverage": 5})
print(f"    {code}: {text}")

# Test leverage with exchange in QUERY
print("\n  Leverage with exchange in QUERY:")
code, text = cs_post("/trade/api/v2/futures/leverage",
    {"symbol": "BTCUSDT", "leverage": 5}, params={"exchange": "EXCHANGE_2"})
print(f"    {code}: {text}")

# Test leverage with exchange in BOTH
print("\n  Leverage with exchange in BOTH:")
code, text = cs_post("/trade/api/v2/futures/leverage",
    {"exchange": "EXCHANGE_2", "symbol": "BTCUSDT", "leverage": 5}, params={"exchange": "EXCHANGE_2"})
print(f"    {code}: {text}")

# Test order endpoint with exchange in BODY only (old way)
print("\n  Order with exchange in BODY only:")
code, text = cs_post("/trade/api/v2/futures/order",
    {"exchange": "EXCHANGE_2", "symbol": "BTCUSDT", "side": "BUY", "order_type": "MARKET",
     "quantity": 0.00001, "reduce_only": False, "leverage": 5})
print(f"    {code}: {text}")

# Test order endpoint with exchange in QUERY only (new way)
print("\n  Order with exchange in QUERY only:")
code, text = cs_post("/trade/api/v2/futures/order",
    {"symbol": "BTCUSDT", "side": "BUY", "order_type": "MARKET",
     "quantity": 0.00001, "reduce_only": False, "leverage": 5},
    params={"exchange": "EXCHANGE_2"})
print(f"    {code}: {text}")

# Test order with exchange in BOTH
print("\n  Order with exchange in BOTH:")
code, text = cs_post("/trade/api/v2/futures/order",
    {"exchange": "EXCHANGE_2", "symbol": "BTCUSDT", "side": "BUY", "order_type": "MARKET",
     "quantity": 0.00001, "reduce_only": False, "leverage": 5},
    params={"exchange": "EXCHANGE_2"})
print(f"    {code}: {text}")

# Test transfer with exchange in BODY only
print("\n  Transfer with exchange in BODY only:")
code, text = cs_post("/trade/api/v2/futures/transfer",
    {"exchange": "EXCHANGE_2", "direction": "IN", "amount": 0.01, "currency": "INR"})
print(f"    {code}: {text}")

# Test transfer with exchange in QUERY only
print("\n  Transfer with exchange in QUERY only:")
code, text = cs_post("/trade/api/v2/futures/transfer",
    {"direction": "IN", "amount": 0.01, "currency": "INR"},
    params={"exchange": "EXCHANGE_2"})
print(f"    {code}: {text}")
