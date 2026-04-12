"""E2E test: CoinDCX open SHORT -> verify via trades -> close -> verify gone."""
import json, sys, time, logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt='%H:%M:%S')
sys.path.insert(0, '.')

from src.connectors.coindcx import CoinDCXConnector

with open('config.json') as f:
    cfg = json.load(f)

cdcx = CoinDCXConnector(cfg)

SYMBOL = 'PIPPINUSDT'

# Step 0: Confirm no position
print("=== Step 0: Confirm clean state ===")
pos = cdcx.get_position(SYMBOL)
if pos:
    print(f"  WARNING: Position already exists: {pos}")
    sys.exit(1)
print("  No position. Good.")

bal = cdcx.get_balance_usdt()
print(f"  Balance: ${bal:.4f}")

# Step 1: Open SHORT
print("\n=== Step 1: Open SHORT 133 qty 5x ===")
try:
    res = cdcx.open_short(SYMBOL, 133, leverage=5)
    print(f"  Order response type: {type(res).__name__}")
    if isinstance(res, list) and res:
        r = res[0]
        print(f"  id={r.get('id')}, side={r.get('side')}, qty={r.get('total_quantity')}, status={r.get('status')}")
    elif isinstance(res, dict):
        print(f"  {json.dumps(res, indent=2)[:300]}")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

# Step 2: Verify position via trades
print("\n=== Step 2: Verify position (trades-based) ===")
time.sleep(1)
pos = cdcx.get_position(SYMBOL)
if pos:
    print(f"  FOUND: qty={pos['quantity']}, side={pos.get('position_side')}, avg_price={pos.get('avg_price')}")
else:
    print("  NOT FOUND — trades-based detection failed!")
    print("  Attempting close anyway...")

# Step 3: Close SHORT (buy)
print("\n=== Step 3: Close SHORT (buy 133) ===")
try:
    res = cdcx.close_short(SYMBOL, 133)
    print(f"  Close response type: {type(res).__name__}")
    if isinstance(res, list) and res:
        r = res[0]
        print(f"  id={r.get('id')}, side={r.get('side')}, qty={r.get('total_quantity')}, status={r.get('status')}")
    elif isinstance(res, dict):
        print(f"  {json.dumps(res, indent=2)[:300]}")
except Exception as e:
    print(f"  CLOSE FAILED: {e}")
    sys.exit(1)

# Step 4: Verify closed
print("\n=== Step 4: Verify position closed ===")
time.sleep(1)
pos = cdcx.get_position(SYMBOL)
if pos:
    print(f"  STILL OPEN: qty={pos['quantity']}")
else:
    print(f"  CLOSED OK — no position detected")

# Step 5: Final balance
bal2 = cdcx.get_balance_usdt()
print(f"\n=== Final balance: ${bal2:.4f} (was ${bal:.4f}, delta: ${bal2-bal:+.4f}) ===")
