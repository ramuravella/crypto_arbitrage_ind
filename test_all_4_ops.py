"""
Direct test of all 4 operations on both exchanges.
Tests: CoinSwitch entry, CoinDCX entry, CoinSwitch exit, CoinDCX exit
Uses a cheap symbol with small qty.
"""
import json, sys, time
sys.path.insert(0, '.')

with open('config.json') as f:
    cfg = json.load(f)

from src.connectors.coinswitch import CoinSwitchConnector
from src.connectors.coindcx import CoinDCXConnector

cs = CoinSwitchConnector(cfg)
cdcx = CoinDCXConnector(cfg)

# Pick a cheap symbol - PIPPINUSDT @ ~$0.05
SYMBOL = 'PIPPINUSDT'
QTY = 133  # minimum for this symbol
LEV = 5

"""
Direct test of all 4 operations on CoinDCX and Delta only.
Tests: CoinDCX entry, CoinDCX exit, Delta entry, Delta exit
Uses a cheap symbol with small qty.
"""
import json, sys, time
sys.path.insert(0, '.')

with open('config.json') as f:
    cfg = json.load(f)

from src.connectors.coindcx import CoinDCXConnector
from src.connectors.delta import DeltaConnector

cdcx = CoinDCXConnector(cfg)
delta = DeltaConnector(cfg)

# Pick a cheap symbol - e.g., BTCUSDT or any available
SYMBOL = 'BTCUSDT'
QTY = 1  # minimum for this symbol
LEV = 1

print("=" * 60)
print(f"TESTING ALL 4 OPERATIONS ON {SYMBOL} qty={QTY} lev={LEV}")
print("=" * 60)

# Check balances first
print("\n--- BALANCES ---")
cdcx_bal = cdcx.get_balance_usdt()
delta_bal = delta.get_balance_usdt()
print(f"  CoinDCX USDT:    {cdcx_bal}")
print(f"  Delta USDT:      {delta_bal}")

# Check existing positions
print("\n--- EXISTING POSITIONS ---")
cdcx_pos = cdcx.get_position(SYMBOL)
delta_pos = delta.get_position(SYMBOL) if hasattr(delta, 'get_position') else None
print(f"  CoinDCX: {cdcx_pos}")
print(f"  Delta:   {delta_pos}")

# ============================
# TEST 1: CoinDCX ENTRY (BUY/LONG)
# ============================
print("\n" + "=" * 60)
print("TEST 1: CoinDCX ENTRY (open_long)")
print("=" * 60)
try:
    t0 = time.time()
    res = cdcx.open_long(SYMBOL, QTY, LEV)
    t1 = time.time()
    print(f"  Time: {t1-t0:.1f}s")
    print(f"  Response: {json.dumps(res, indent=2, default=str)}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()

# ============================
# TEST 2: CoinDCX EXIT (close_long)
# ============================
print("\n" + "=" * 60)
print("TEST 2: CoinDCX EXIT (close_long)")
print("=" * 60)
try:
    t0 = time.time()
    res = cdcx.close_long(SYMBOL, QTY)
    t1 = time.time()
    print(f"  Time: {t1-t0:.1f}s")
    print(f"  Response: {json.dumps(res, indent=2, default=str)}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()

# ============================
# TEST 3: Delta ENTRY (open_long)
# ============================
print("\n" + "=" * 60)
print("TEST 3: Delta ENTRY (open_long)")
print("=" * 60)
if hasattr(delta, 'open_long'):
    try:
        t0 = time.time()
        res = delta.open_long(SYMBOL, QTY, LEV)
        t1 = time.time()
        print(f"  Time: {t1-t0:.1f}s")
        print(f"  Response: {json.dumps(res, indent=2, default=str)}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()
else:
    print("  DeltaConnector does not implement open_long().")

# ============================
# TEST 4: Delta EXIT (close_long)
# ============================
print("\n" + "=" * 60)
print("TEST 4: Delta EXIT (close_long)")
print("=" * 60)
if hasattr(delta, 'close_long'):
    try:
        t0 = time.time()
        res = delta.close_long(SYMBOL, QTY)
        t1 = time.time()
        print(f"  Time: {t1-t0:.1f}s")
        print(f"  Response: {json.dumps(res, indent=2, default=str)}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()
else:
    print("  DeltaConnector does not implement close_long().")
        for i in range(5):
            time.sleep(1)
            pos = cdcx.get_position(SYMBOL)
            if not pos:
                print(f"    Attempt {i+1}: Position closed!")
                break
            else:
                q = float(pos.get('quantity', pos.get('qty', 0)) or 0)
                print(f"    Attempt {i+1}: still open, qty={q}")
        else:
            print("  *** POSITION STILL OPEN AFTER 5 SECONDS ***")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()
else:
    print("  SKIPPED — no CoinDCX position to close")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
