import json, time, requests, hmac, hashlib
from cryptography.hazmat.primitives.asymmetric import ed25519

with open('config.json') as f:
    cfg = json.load(f)

CS_KEY = cfg['exchanges']['coinswitch']['api_key']
CS_SECRET = cfg['exchanges']['coinswitch']['api_secret']
CDCX_KEY = cfg['exchanges']['coindcx']['api_key']
CDCX_SECRET = cfg['exchanges']['coindcx']['api_secret']

# CoinSwitch
epoch = str(int(time.time() * 1000))
path = '/trade/api/v2/futures/positions?exchange=EXCHANGE_2'
msg = 'GET' + path + epoch
priv = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(CS_SECRET))
sig = priv.sign(msg.encode()).hex()
hdrs = {'Content-Type': 'application/json', 'X-AUTH-APIKEY': CS_KEY,
        'X-AUTH-SIGNATURE': sig, 'X-AUTH-EPOCH': epoch}
r = requests.get('https://coinswitch.co' + path, headers=hdrs, timeout=10)

print('=== COINSWITCH POSITIONS ===')
if r.ok:
    positions = r.json().get('data', [])
    if not positions:
        print('  No positions')
    for p in positions:
        sym = p.get('symbol', '?')
        side = p.get('position_side', '?')
        qty = p.get('position_size', '?')
        pnl = p.get('unrealised_pnl', '?')
        entry = p.get('avg_entry_price', '?')
        mark = p.get('mark_price', '?')
        print(f'  {sym} | side={side} | qty={qty} | pnl={pnl} | entry={entry} | mark={mark}')
else:
    print(f'  ERROR: {r.status_code} {r.text[:200]}')

# CoinDCX
payload = {'timestamp': int(time.time() * 1000)}
body = json.dumps(payload, separators=(',', ':'))
sig2 = hmac.new(CDCX_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
hdrs2 = {'Content-Type': 'application/json', 'X-AUTH-APIKEY': CDCX_KEY,
         'X-AUTH-SIGNATURE': sig2}
r2 = requests.post('https://api.coindcx.com/exchange/v1/derivatives/futures/positions',
                    data=body, headers=hdrs2, timeout=10)

print()
print('=== COINDCX POSITIONS ===')
if r2.ok:
    data = r2.json()
    found = False
    for p in (data if isinstance(data, list) else []):
        ap = float(p.get('active_pos', 0))
        if ap != 0:
            found = True
            side = 'LONG' if ap > 0 else 'SHORT'
            pair = p.get('pair', '?')
            avg = p.get('avg_price', '?')
            mark = p.get('mark_price', '?')
            margin = p.get('margin_currency_short_name', '?')
            print(f'  {pair} | side={side} | active_pos={ap} | avg_price={avg} | mark={mark} | margin={margin}')
    if not found:
        print('  No active positions (all active_pos=0)')
else:
    print(f'  ERROR: {r2.status_code} {r2.text[:200]}')
