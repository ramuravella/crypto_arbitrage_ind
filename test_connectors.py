"""
Test the actual connectors (not raw HTTP) to confirm each operation.
Tests: get_position on both, close_long on CoinSwitch (PIPPIN orphan).
"""
"""
Test the actual connectors (not raw HTTP) to confirm each operation.
Tests: get_position and get_balance_usdt on CoinDCX and Delta.
"""
import json, sys, logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s: %(message)s')

sys.path.insert(0, '.')
from src.connectors.coindcx import CoinDCXConnector
from src.connectors.delta import DeltaConnector

with open('config.json') as f:
    cfg = json.load(f)

cdcx = CoinDCXConnector(cfg)
delta = DeltaConnector(cfg)

print("=" * 60)
print("TEST 1: CoinDCX get_position('BTCUSDT')")
print("=" * 60)
try:
    pos = cdcx.get_position('BTCUSDT')
    if pos:
        print(f"  FOUND! qty={pos.get('quantity')}, side={pos.get('position_side', pos.get('active_pos', ''))}")
        print(f"  entry={pos.get('avg_entry_price')}, mark={pos.get('mark_price')}")
        print(f"  pnl={pos.get('unrealised_pnl', pos.get('pnl', ''))}")
    else:
        print("  None returned — no position found")
except Exception as e:
    print(f"  EXCEPTION: {e}")

print("\n" + "=" * 60)
print("TEST 2: Delta get_position('BTCUSDT')")
print("=" * 60)
if hasattr(delta, 'get_position'):
    try:
        pos = delta.get_position('BTCUSDT')
        if pos:
            print(f"  FOUND! qty={pos.get('quantity')}, side={pos.get('position_side', pos.get('active_pos', ''))}")
            print(f"  entry={pos.get('avg_entry_price')}, mark={pos.get('mark_price')}")
            print(f"  pnl={pos.get('unrealised_pnl', pos.get('pnl', ''))}")
        else:
            print("  None returned — no position found")
    except Exception as e:
        print(f"  EXCEPTION: {e}")
else:
    print("  DeltaConnector does not implement get_position().")

print("\n" + "=" * 60)
print("TEST 3: CoinDCX get_balance_usdt()")
print("=" * 60)
try:
    bal = cdcx.get_balance_usdt()
    print(f"  Balance: {bal} USDT")
except Exception as e:
    print(f"  EXCEPTION: {e}")

print("\n" + "=" * 60)
print("TEST 4: Delta get_balance_usdt()")
print("=" * 60)
try:
    bal = delta.get_balance_usdt()
    print(f"  Balance: {bal} USDT")
except Exception as e:
    print(f"  EXCEPTION: {e}")

print("\n" + "=" * 60)
print("All tests complete.")
        pos = cs.get_position('PIPPINUSDT')
        if pos:
            print(f"  STILL OPEN! qty={pos.get('quantity')}")
        else:
            print(f"  CLOSED SUCCESSFULLY - position gone")
    except Exception as e:
        print(f"  VERIFY EXCEPTION: {e}")
else:
    print("  Skipped.")
