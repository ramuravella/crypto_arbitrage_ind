"""Quick test of CoinDCX symbol mapping & active instruments."""
import json, sys, logging, requests
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
sys.path.insert(0, '.')

# Test 1: Active instruments
print("TEST 1: active_instruments endpoint")
r = requests.get("https://api.coindcx.com/exchange/v1/derivatives/futures/data/active_instruments", timeout=10)
print(f"  Status: {r.status_code}, Count: {len(r.json()) if r.ok else '?'}")
if r.ok:
    instruments = r.json()
    pippin = [x for x in instruments if 'PIPPIN' in x.upper()]
    print(f"  PIPPIN matches: {pippin}")
    if not pippin:
        print("  WARNING: PIPPIN not in active instruments!")
    # Show a few examples
    print(f"  First 5: {instruments[:5]}")

# Test 2: Connector's _raw_sym
from src.connectors.coindcx import CoinDCXConnector
with open('config.json') as f:
    cfg = json.load(f)
cdcx = CoinDCXConnector(cfg)

print("\nTEST 2: _raw_sym conversion")
for sym in ['PIPPINUSDT', 'BTCUSDT', 'ETHUSDT', 'DRIFTUSDT', 'HEMIUSDT']:
    raw = cdcx._raw_sym(sym)
    print(f"  {sym} -> {raw}")
