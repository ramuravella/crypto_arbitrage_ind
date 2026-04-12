"""
Full E2E Test: Entry + Exit on both exchanges.
Sequence:
  1. Check balances & any existing positions
  2. Close any orphaned positions first (CoinSwitch PIPPIN)
  3. Pick a cheap symbol, compute min qty
  4. ENTRY: CoinSwitch LONG + CoinDCX SHORT (sequential)
  5. Verify both positions exist
  6. EXIT: Close both positions
  7. Verify both closed
  8. Final balance check
"""
import json, sys, time, logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-5s %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('E2E')
sys.path.insert(0, '.')

from src.connectors.coinswitch import CoinSwitchConnector
from src.connectors.coindcx import CoinDCXConnector

with open('config.json') as f:
    cfg = json.load(f)

cs = CoinSwitchConnector(cfg)
cdcx = CoinDCXConnector(cfg)

SYMBOL = 'PIPPINUSDT'
LEVERAGE = 5

def sep(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")

# ─── STEP 0: Current state ───────────────────────────────────────────────
sep("STEP 0: Current State")

cs_bal = cs.get_balance_usdt()
cdcx_bal = cdcx.get_balance_usdt()
print(f"  CoinSwitch balance: ${cs_bal:.4f}")
print(f"  CoinDCX balance:    ${cdcx_bal:.4f}")

cs_pos = cs.get_position(SYMBOL)
cdcx_pos = cdcx.get_position(SYMBOL)
cs_info = f"qty={cs_pos['quantity']}, side={cs_pos.get('position_side')}" if cs_pos else 'None'
cdcx_info = f"qty={cdcx_pos['quantity']}, active_pos={cdcx_pos.get('active_pos')}" if cdcx_pos else 'None'
print(f"  CoinSwitch {SYMBOL}: {cs_info}")
print(f"  CoinDCX    {SYMBOL}: {cdcx_info}")

# ─── STEP 1: Close orphans ───────────────────────────────────────────────
if cs_pos:
    sep("STEP 1a: Close orphaned CoinSwitch position")
    side = cs_pos.get('position_side', '').upper()
    qty = cs_pos['quantity']
    print(f"  Closing {side} {qty} on CoinSwitch...")
    try:
        if side == 'LONG':
            res = cs.close_long(SYMBOL, qty)
        else:
            res = cs.close_short(SYMBOL, qty)
        print(f"  Order result: {json.dumps(res, indent=2) if isinstance(res, dict) else res}")
    except Exception as e:
        print(f"  FAILED: {e}")
        print("  Cannot proceed with orphan open. Exiting.")
        sys.exit(1)
    
    # Poll for close
    for i in range(8):
        time.sleep(1)
        p = cs.get_position(SYMBOL)
        if not p:
            print(f"  Closed after {i+1}s")
            break
        pq = p['quantity']
        print(f"  Still open after {i+1}s: qty={pq}")
    else:
        print("  WARNING: CoinSwitch position may still be open!")

if cdcx_pos:
    sep("STEP 1b: Close orphaned CoinDCX position")
    qty = cdcx_pos['quantity']
    ap = float(cdcx_pos.get('active_pos', 0))
    print(f"  active_pos={ap}, closing...")
    try:
        if ap > 0:  # long
            res = cdcx.close_long(SYMBOL, qty)
        else:
            res = cdcx.close_short(SYMBOL, qty)
        print(f"  Order result: {json.dumps(res, indent=2) if isinstance(res, dict) else res}")
    except Exception as e:
        print(f"  FAILED: {e}")

    time.sleep(1)
    p = cdcx.get_position(SYMBOL)
    after_msg = 'gone' if not p else f"qty={p['quantity']}"
    print(f"  After close: {after_msg}")

# Refresh balances after orphan cleanup
time.sleep(1)
cs_bal = cs.get_balance_usdt()
cdcx_bal = cdcx.get_balance_usdt()
print(f"\n  Post-cleanup balances:")
print(f"  CoinSwitch: ${cs_bal:.4f}")
print(f"  CoinDCX:    ${cdcx_bal:.4f}")

# ─── STEP 2: Determine trade size ────────────────────────────────────────
sep("STEP 2: Determine Trade Size")

# Get PIPPIN price from CoinSwitch
import requests
try:
    # Use Binance public API for price
    r = requests.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={SYMBOL}", timeout=5)
    price = float(r.json()['price'])
    print(f"  {SYMBOL} price: ${price:.6f}")
except Exception as e:
    print(f"  Binance price fetch failed: {e}")
    price = 0.06  # fallback
    print(f"  Using fallback price: ${price}")

# Calculate qty: use $1 notional with leverage
notional_usd = 1.0
qty = notional_usd * LEVERAGE / price
# Round to integer for PIPPIN (typical min_qty step)
qty = max(int(qty), 1)
print(f"  Notional: ${notional_usd} x {LEVERAGE}x leverage")
print(f"  Calculated qty: {qty}")
print(f"  Position value: ${qty * price:.4f}")
print(f"  Margin needed: ${qty * price / LEVERAGE:.4f}")

min_bal = qty * price / LEVERAGE * 1.1  # 10% buffer
if cs_bal < min_bal or cdcx_bal < min_bal:
    print(f"\n  WARNING: Low balance! Need ~${min_bal:.2f} per exchange")
    print(f"  CoinSwitch: ${cs_bal:.4f}, CoinDCX: ${cdcx_bal:.4f}")
    if cs_bal < min_bal * 0.5 or cdcx_bal < min_bal * 0.5:
        print("  Balance too low to proceed. Exiting.")
        sys.exit(1)

# ─── STEP 3: ENTRY — CoinSwitch LONG first, then CoinDCX SHORT ──────────
sep("STEP 3: ENTRY")

print(f"  Step 3a: CoinSwitch LONG {SYMBOL} qty={qty} lev={LEVERAGE}x...")
cs_entry_time = time.time()
try:
    cs_order = cs.open_long(SYMBOL, qty, leverage=LEVERAGE)
    print(f"  CS order response: {json.dumps(cs_order, indent=2) if isinstance(cs_order, dict) else cs_order}")
except Exception as e:
    print(f"  CS LONG FAILED: {e}")
    print("  Aborting entry.")
    sys.exit(1)

# Poll CoinSwitch for fill
print(f"\n  Step 3b: Polling CoinSwitch for fill...")
cs_filled = False
for i in range(10):
    time.sleep(1)
    p = cs.get_position(SYMBOL)
    if p and p.get('quantity', 0) > 0:
        elapsed = time.time() - cs_entry_time
        print(f"  CS FILLED in {elapsed:.1f}s: qty={p['quantity']}, side={p.get('position_side')}")
        print(f"    entry_price={p.get('avg_entry_price')}, mark={p.get('mark_price')}")
        cs_filled = True
        break
    print(f"  Poll {i+1}: not filled yet...")

if not cs_filled:
    print("  CS position NOT FOUND after 10 polls! Something failed.")
    print("  Check CoinSwitch manually. Aborting.")
    sys.exit(1)

# CoinDCX SHORT
print(f"\n  Step 3c: CoinDCX SHORT {SYMBOL} qty={qty} lev={LEVERAGE}x...")
cdcx_entry_time = time.time()
try:
    cdcx_order = cdcx.open_short(SYMBOL, qty, leverage=LEVERAGE)
    print(f"  CDCX order response: {json.dumps(cdcx_order, indent=2) if isinstance(cdcx_order, dict) else cdcx_order}")
except Exception as e:
    print(f"  CDCX SHORT FAILED: {e}")
    print("  PANIC: Closing CoinSwitch LONG...")
    try:
        cs.close_long(SYMBOL, qty)
        time.sleep(2)
        p = cs.get_position(SYMBOL)
        panic_msg = 'success' if not p else f"STILL OPEN qty={p['quantity']}"
        print(f"  Panic close: {panic_msg}")
    except Exception as e2:
        print(f"  PANIC CLOSE ALSO FAILED: {e2}")
    sys.exit(1)

# Verify CoinDCX position
print(f"\n  Step 3d: Verifying CoinDCX position...")
cdcx_filled = False
for i in range(5):
    time.sleep(0.5)
    p = cdcx.get_position(SYMBOL)
    if p:
        elapsed = time.time() - cdcx_entry_time
        print(f"  CDCX FOUND in {elapsed:.1f}s: qty={p['quantity']}, active_pos={p.get('active_pos')}")
        print(f"    avg_price={p.get('avg_price')}, mark={p.get('mark_price')}")
        cdcx_filled = True
        break
    print(f"  Poll {i+1}: not found yet...")

if not cdcx_filled:
    print("  CDCX position NOT FOUND!")
    print("  Note: CoinDCX may report active_pos=0 even after fill.")
    print("  Checking raw positions...")
    try:
        data = cdcx._signed_post("/exchange/v1/derivatives/futures/positions", {})
        for pp in (data if isinstance(data, list) else []):
            if 'PIPPIN' in str(pp.get('pair', '')).upper():
                print(f"    Raw: pair={pp['pair']}, active_pos={pp['active_pos']}, "
                      f"avg_price={pp.get('avg_price')}, margin={pp.get('margin_currency_short_name')}")
    except Exception as e:
        print(f"    Raw check failed: {e}")

# ─── STEP 4: Both positions status ───────────────────────────────────────
sep("STEP 4: Position Verification")
time.sleep(1)

cs_pos = cs.get_position(SYMBOL)
cdcx_pos = cdcx.get_position(SYMBOL)
cs_info2 = f"qty={cs_pos['quantity']}, side={cs_pos.get('position_side')}" if cs_pos else 'NONE'
cdcx_info2 = f"qty={cdcx_pos['quantity']}, active_pos={cdcx_pos.get('active_pos')}" if cdcx_pos else 'NONE'
print(f"  CoinSwitch: {cs_info2}")
print(f"  CoinDCX:    {cdcx_info2}")

if cs_pos and cdcx_pos:
    print("  BOTH POSITIONS CONFIRMED — hedge is active ✓")
elif cs_pos and not cdcx_pos:
    print("  WARNING: Only CoinSwitch has position — CoinDCX may show 0 active_pos")
    print("  Proceeding to exit attempt anyway...")
elif not cs_pos:
    print("  CRITICAL: CoinSwitch position missing!")
    sys.exit(1)

print("\n  Waiting 3s before exit test...")
time.sleep(3)

# ─── STEP 5: EXIT — Close both legs ──────────────────────────────────────
sep("STEP 5: EXIT")

# Close CoinSwitch first (slow leg)
print(f"  Step 5a: Close CoinSwitch LONG...")
try:
    if cs_pos:
        cs_close = cs.close_long(SYMBOL, cs_pos['quantity'])
        print(f"  CS close result: {json.dumps(cs_close, indent=2) if isinstance(cs_close, dict) else cs_close}")
except Exception as e:
    print(f"  CS CLOSE FAILED: {e}")

# Close CoinDCX
print(f"\n  Step 5b: Close CoinDCX SHORT...")
try:
    close_qty = cdcx_pos['quantity'] if cdcx_pos else qty
    cdcx_close = cdcx.close_short(SYMBOL, close_qty)
    print(f"  CDCX close result: {json.dumps(cdcx_close, indent=2) if isinstance(cdcx_close, dict) else cdcx_close}")
except Exception as e:
    print(f"  CDCX CLOSE FAILED: {e}")

# ─── STEP 6: Verify both closed ──────────────────────────────────────────
sep("STEP 6: Exit Verification")

for i in range(8):
    time.sleep(1)
    cs_p = cs.get_position(SYMBOL)
    cdcx_p = cdcx.get_position(SYMBOL)
    cs_status = f"qty={cs_p['quantity']}" if cs_p else "CLOSED"  # noqa
    cdcx_status = f"qty={cdcx_p['quantity']}" if cdcx_p else "CLOSED"  # noqa
    print(f"  Poll {i+1}: CS={cs_status}, CDCX={cdcx_status}")
    if not cs_p and not cdcx_p:
        print(f"  BOTH CLOSED after {i+1}s ✓")
        break
else:
    print("  WARNING: Positions may still be open after 8s polling!")
    if cs_p:
        print(f"  CoinSwitch STILL OPEN: qty={cs_p['quantity']}")
    if cdcx_p:
        print(f"  CoinDCX STILL OPEN: qty={cdcx_p['quantity']}")

# ─── STEP 7: Final balances ──────────────────────────────────────────────
sep("STEP 7: Final Balances")
time.sleep(1)
cs_bal_final = cs.get_balance_usdt()
cdcx_bal_final = cdcx.get_balance_usdt()
print(f"  CoinSwitch: ${cs_bal_final:.4f}  (was ${cs_bal:.4f}, delta: ${cs_bal_final-cs_bal:+.4f})")
print(f"  CoinDCX:    ${cdcx_bal_final:.4f}  (was ${cdcx_bal:.4f}, delta: ${cdcx_bal_final-cdcx_bal:+.4f})")
print(f"  Net change: ${(cs_bal_final-cs_bal)+(cdcx_bal_final-cdcx_bal):+.4f}")

sep("TEST COMPLETE")
