"""
End-to-end test: CoinDCX open + close, then CoinSwitch close orphan.
Uses actual connectors. PIPPIN is cheap enough for small test.
"""
import json, sys, time, logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
sys.path.insert(0, '.')

from src.connectors.coindcx import CoinDCXConnector
from src.connectors.coinswitch import CoinSwitchConnector

with open('config.json') as f:
    cfg = json.load(f)

cdcx = CoinDCXConnector(cfg)
cs = CoinSwitchConnector(cfg)

print("\n" + "=" * 60)
print("STEP 1: CoinDCX — Open SHORT PIPPINUSDT (133 qty, 5x)")
print("  This matches the orphan CoinSwitch LONG position")
print("=" * 60)

confirm = input("  Type 'test' to open CoinDCX short + then close CoinSwitch long,\n  or 'skip' to skip: ").strip().lower()

if confirm == 'test':
    # Open CoinDCX short
    print("\n  Opening CoinDCX SHORT...")
    try:
        res = cdcx.open_short('PIPPINUSDT', 133, leverage=5)
        print(f"  ORDER RESULT: {json.dumps(res, indent=2) if isinstance(res, dict) else res}")
    except Exception as e:
        print(f"  FAILED: {e}")
        sys.exit(1)
    
    time.sleep(1)
    
    # Verify CoinDCX position
    print("\n  Checking CoinDCX position...")
    pos = cdcx.get_position('PIPPINUSDT')
    if pos:
        print(f"  CoinDCX POSITION FOUND: qty={pos.get('quantity')}, active_pos={pos.get('active_pos')}")
    else:
        print(f"  CoinDCX position NOT FOUND (active_pos=0)")
    
    time.sleep(1)
    
    # Now close BOTH positions
    print("\n" + "=" * 60)
    print("STEP 2: Close BOTH legs")
    print("=" * 60)
    
    # Close CoinDCX short
    print("\n  Closing CoinDCX SHORT...")
    try:
        res = cdcx.close_short('PIPPINUSDT', 133)
        print(f"  CLOSE RESULT: {json.dumps(res, indent=2) if isinstance(res, dict) else res}")
    except Exception as e:
        print(f"  CLOSE FAILED: {e}")
    
    time.sleep(1)
    
    # Verify CoinDCX closed
    print("\n  Verifying CoinDCX position closed...")
    pos = cdcx.get_position('PIPPINUSDT')
    if pos:
        print(f"  WARNING: Still active: qty={pos.get('quantity')}")
    else:
        print(f"  CoinDCX position CLOSED successfully")
    
    # Close CoinSwitch long
    print("\n  Closing CoinSwitch LONG...")
    try:
        res = cs.close_long('PIPPINUSDT', 133)
        print(f"  CLOSE RESULT: {json.dumps(res, indent=2) if isinstance(res, dict) else res}")
    except Exception as e:
        print(f"  CLOSE FAILED: {e}")
    
    time.sleep(2)
    
    # Verify CoinSwitch closed
    print("\n  Verifying CoinSwitch position closed...")
    pos = cs.get_position('PIPPINUSDT')
    if pos:
        print(f"  WARNING: Still active: qty={pos.get('quantity')}")
    else:
        print(f"  CoinSwitch position CLOSED successfully")
    
    # Check balances after
    print("\n" + "=" * 60)
    print("FINAL: Balances")
    print("=" * 60)
    print(f"  CoinDCX:    ${cdcx.get_balance_usdt():.4f}")
    print(f"  CoinSwitch: ${cs.get_balance_usdt():.4f}")
    
elif confirm == 'skip':
    # Just close CoinSwitch orphan
    print("\n" + "=" * 60)
    print("Closing CoinSwitch PIPPIN LONG only")
    print("=" * 60)
    
    confirm2 = input("  Type 'close' to close CoinSwitch PIPPIN LONG: ").strip().lower()
    if confirm2 == 'close':
        try:
            res = cs.close_long('PIPPINUSDT', 133)
            print(f"  RESULT: {json.dumps(res, indent=2) if isinstance(res, dict) else res}")
        except Exception as e:
            print(f"  FAILED: {e}")
        
        time.sleep(2)
        pos = cs.get_position('PIPPINUSDT')
        print(f"  Position after close: {'STILL OPEN' if pos else 'CLOSED'}")
else:
    print("  Skipped all tests.")
