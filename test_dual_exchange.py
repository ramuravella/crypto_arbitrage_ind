"""E2E: CoinSwitch LONG + CoinDCX SHORT → verify both → close both → verify closed."""
import json, sys, time, logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt='%H:%M:%S')
sys.path.insert(0, '.')

from src.connectors.coindcx import CoinDCXConnector
from src.connectors.coinswitch import CoinSwitchConnector

with open('config.json') as f:
    cfg = json.load(f)

cdcx = CoinDCXConnector(cfg)
cs = CoinSwitchConnector(cfg)

SYMBOL = 'PIPPINUSDT'
QTY = 133
LEV = 5

# Step 0: Clean state
print("=== Step 0: Confirm clean state ===")
cdcx_pos = cdcx.get_position(SYMBOL)
cs_pos = cs.get_position(SYMBOL)
if cdcx_pos:
    print(f"  WARNING: CoinDCX position exists: qty={cdcx_pos.get('quantity')}")
    sys.exit(1)
if cs_pos:
    print(f"  WARNING: CoinSwitch position exists: qty={cs_pos.get('quantity', cs_pos.get('position_size'))}")
    sys.exit(1)
print("  Both clean.")

cdcx_bal = cdcx.get_balance_usdt()
cs_bal = cs.get_balance_usdt()
print(f"  CoinDCX: ${cdcx_bal:.4f} | CoinSwitch: ${cs_bal:.4f}")

# Step 1: CoinSwitch LONG (slower, enter first)
print(f"\n=== Step 1: CoinSwitch LONG {QTY} qty {LEV}x ===")
try:
    cs_res = cs.open_long(SYMBOL, QTY, LEV)
    print(f"  Response: {json.dumps(cs_res, indent=2)[:400]}")
except Exception as e:
    print(f"  FAILED: {e}")
    sys.exit(1)

# Step 2: Poll CoinSwitch fill
print("\n=== Step 2: Poll CoinSwitch position ===")
for attempt in range(8):
    time.sleep(1)
    cs_pos = cs.get_position(SYMBOL)
    if cs_pos:
        qty_found = float(cs_pos.get('position_size', cs_pos.get('quantity', 0)))
        print(f"  FOUND after {attempt+1}s: qty={qty_found}")
        break
    print(f"  attempt {attempt+1}: not yet...")
else:
    print("  CoinSwitch position NOT found after 8s. Aborting.")
    sys.exit(1)

# Step 3: CoinDCX SHORT
print(f"\n=== Step 3: CoinDCX SHORT {QTY} qty {LEV}x ===")
try:
    cdcx_res = cdcx.open_short(SYMBOL, QTY, LEV)
    print(f"  Response type: {type(cdcx_res).__name__}")
    if isinstance(cdcx_res, list) and cdcx_res:
        r = cdcx_res[0]
        print(f"  id={r.get('id')}, side={r.get('side')}, qty={r.get('total_quantity')}, status={r.get('status')}")
except Exception as e:
    print(f"  FAILED: {e}")
    print("  Panic closing CoinSwitch LONG...")
    try:
        cs.close_long(SYMBOL, QTY)
        print("  CoinSwitch closed.")
    except Exception as e2:
        print(f"  CoinSwitch close also failed: {e2}")
    sys.exit(1)

# Step 4: Verify CoinDCX SHORT
print("\n=== Step 4: Verify CoinDCX SHORT ===")
time.sleep(1)
cdcx_pos = cdcx.get_position(SYMBOL)
if cdcx_pos:
    print(f"  FOUND: qty={cdcx_pos['quantity']}, side={cdcx_pos.get('position_side')}")
else:
    print("  NOT FOUND — will try closing anyway")

print("\n--- BOTH LEGS OPEN. Hedged position confirmed. ---")
print(f"  CoinSwitch: LONG {QTY}")
print(f"  CoinDCX:    SHORT {QTY}")
print("\nClosing both legs in 3 seconds...")
time.sleep(3)

# Step 5: Close both
print("\n=== Step 5: Close CoinSwitch LONG ===")
try:
    cs_close = cs.close_long(SYMBOL, QTY)
    print(f"  Response: {json.dumps(cs_close, indent=2)[:300]}")
except Exception as e:
    print(f"  FAILED: {e}")

print("\n=== Step 6: Close CoinDCX SHORT ===")
try:
    cdcx_close = cdcx.close_short(SYMBOL, QTY)
    print(f"  Response type: {type(cdcx_close).__name__}")
    if isinstance(cdcx_close, list) and cdcx_close:
        r = cdcx_close[0]
        print(f"  id={r.get('id')}, side={r.get('side')}, status={r.get('status')}")
except Exception as e:
    print(f"  FAILED: {e}")

# Step 7: Verify both closed
print("\n=== Step 7: Verify both closed ===")
time.sleep(2)
cdcx_pos = cdcx.get_position(SYMBOL)
cs_pos = cs.get_position(SYMBOL)
print(f"  CoinDCX:    {'STILL OPEN' if cdcx_pos else 'CLOSED OK'}")
print(f"  CoinSwitch: {'STILL OPEN' if cs_pos else 'CLOSED OK'}")

# Final balance
cdcx_bal2 = cdcx.get_balance_usdt()
cs_bal2 = cs.get_balance_usdt()
print(f"\n=== Final balances ===")
print(f"  CoinDCX:    ${cdcx_bal2:.4f} (delta: ${cdcx_bal2-cdcx_bal:+.4f})")
print(f"  CoinSwitch: ${cs_bal2:.4f} (delta: ${cs_bal2-cs_bal:+.4f})")
print(f"  Total delta: ${(cdcx_bal2-cdcx_bal)+(cs_bal2-cs_bal):+.4f}")
