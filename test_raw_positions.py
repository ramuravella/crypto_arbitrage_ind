"""Debug: raw positions from both exchanges"""
import json, sys
sys.path.insert(0, '.')

with open('config.json') as f:
    cfg = json.load(f)

from src.connectors.coinswitch import CoinSwitchConnector
from src.connectors.coindcx import CoinDCXConnector

cs = CoinSwitchConnector(cfg)
cdcx = CoinDCXConnector(cfg)

# Raw CoinDCX positions
print("=== RAW CoinDCX positions ===")
try:
    raw = cdcx._signed_post("/exchange/v1/derivatives/futures/positions", {})
    if isinstance(raw, list):
        print(f"  Got {len(raw)} positions:")
        for p in raw:
            pair = p.get('pair', p.get('symbol', ''))
            active = p.get('active_pos', 0)
            qty = p.get('quantity', 0)
            side = p.get('side', '')
            print(f"    pair={pair} active_pos={active} quantity={qty} side={side}")
            if 'PIPPIN' in str(pair).upper():
                print(f"    FULL: {json.dumps(p, indent=2, default=str)}")
    else:
        print(f"  Raw response: {json.dumps(raw, indent=2, default=str)[:2000]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Raw CoinSwitch positions
print("\n=== RAW CoinSwitch positions ===")
try:
    raw = cs._get("/trade/api/v2/futures/positions", params={"exchange": "EXCHANGE_2"})
    print(f"  Raw response: {json.dumps(raw, indent=2, default=str)[:2000]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Also check CoinDCX orders
print("\n=== RAW CoinDCX open orders ===")
try:
    raw = cdcx._signed_post("/exchange/v1/derivatives/futures/orders/active_orders", {})
    if isinstance(raw, list):
        print(f"  Got {len(raw)} active orders")
        for o in raw[:5]:
            print(f"    pair={o.get('pair')} side={o.get('side')} status={o.get('status')} remaining={o.get('remaining_quantity')} lev={o.get('leverage')}")
    else:
        print(f"  Response: {json.dumps(raw, indent=2, default=str)[:1000]}")
except Exception as e:
    print(f"  ERROR: {e}")
