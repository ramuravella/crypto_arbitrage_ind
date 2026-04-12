"""Check CoinDCX instruments for margin currency info"""
import json, sys
sys.path.insert(0, '.')

with open('config.json') as f:
    cfg = json.load(f)

from src.connectors.coindcx import CoinDCXConnector
cdcx = CoinDCXConnector(cfg)

# Get active instruments
print("=== CoinDCX Active Instruments (PIPPIN + BTC) ===")
try:
    instruments = cdcx._get_public("/exchange/v1/derivatives/futures/data/active_instruments")
    if isinstance(instruments, list):
        # Just check instrument names
        for inst in instruments:
            if isinstance(inst, str):
                if 'PIPPIN' in inst.upper() or 'BTC' in inst.upper():
                    print(f"  {inst}")
            elif isinstance(inst, dict):
                name = inst.get('pair', inst.get('symbol', ''))
                if 'PIPPIN' in str(name).upper():
                    print(f"  PIPPIN: {json.dumps(inst, indent=2, default=str)}")
                elif 'BTC' in str(name).upper() and 'USDT' in str(name).upper():
                    print(f"  BTC: {json.dumps(inst, indent=2, default=str)[:300]}")
        print(f"  Total instruments: {len(instruments)}")
    else:
        print(f"  Response type: {type(instruments)}")
        print(f"  First 500 chars: {json.dumps(instruments, default=str)[:500]}")
except Exception as e:
    print(f"  ERROR: {e}")

# Try contract info endpoint
print("\n=== Contract details ===")
for endpoint in [
    "/exchange/v1/derivatives/futures/data/contract",
    "/exchange/v1/derivatives/futures/data/contracts",
]:
    try:
        resp = cdcx._get_public(endpoint)
        # Find PIPPIN
        if isinstance(resp, list):
            for item in resp:
                if isinstance(item, dict) and 'PIPPIN' in str(item.get('pair', item.get('symbol', ''))).upper():
                    print(f"  PIPPIN contract: {json.dumps(item, indent=2, default=str)}")
                    break
            else:
                print(f"  {endpoint}: {len(resp)} items, no PIPPIN")
        elif isinstance(resp, dict):
            print(f"  {endpoint}: {json.dumps(resp, default=str)[:300]}")
    except Exception as e:
        print(f"  {endpoint}: ERROR ({e})")
